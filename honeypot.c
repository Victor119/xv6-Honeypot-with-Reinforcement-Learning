// M1: one synthetic request, two kernel-owned pages, one boot agent.
#include "types.h"
#include "defs.h"
#include "param.h"
#include "memlayout.h"
#include "mmu.h"
#include "proc.h"
#include "x86.h"
#include "spinlock.h"
#include "honeypot.h"

// These pages belong to the kernel for the entire boot. User page-table
// teardown must remove their aliases without returning them to kalloc.
static char event_memory[PGSIZE] __attribute__((aligned(PGSIZE)));
static char decision_memory[PGSIZE] __attribute__((aligned(PGSIZE)));
static struct hp_event_page *events = (void*)event_memory;
static struct hp_decision_page *decision = (void*)decision_memory;
typedef char hp_pages_fit[(sizeof(struct hp_event_page) <= PGSIZE &&
                          sizeof(struct hp_decision_page) <= PGSIZE) ? 1 : -1];

struct hp_request {
  uint id;
  uint started;
  int delivered;
  int answered;
  int action;
};

static struct {
  struct spinlock lock;
  struct proc *agent;
  uint next_id;
  struct hp_request *pending;
} hp;

void
hpinit(void)
{
  initlock(&hp.lock, "honeypot");
  hp.next_id = 1;
  memset(event_memory, 0, PGSIZE);
  memset(decision_memory, 0, PGSIZE);
  events->version = HP_ABI_VERSION;
}

int
hp_register_agent(void)
{
  struct proc *me = myproc();

  acquire(&hp.lock);
  if(!me->hp_authorized || me->killed ||
     (hp.agent != 0 && hp.agent != me)){
    release(&hp.lock);
    return HP_ERR_INVALID;
  }
  if(hp.agent == me){
    release(&hp.lock);
    return 0;
  }
  if(maphpages(me->pgdir, event_memory, decision_memory) < 0){
    release(&hp.lock);
    return HP_ERR_INVALID;
  }
  switchuvm(me);
  hp.agent = me;
  release(&hp.lock);
  return 0;
}

void
hp_detach(struct proc *p)
{
  acquire(&hp.lock);
  p->hp_bootstrap = 0;
  p->hp_authorized = 0;
  if(hp.agent == p){
    hp.agent = 0;
    unmaphpages(p->pgdir);
    switchuvm(p);
    events->ready = 0;
    decision->ready = 0;
    wakeup(&ticks);
    wakeup(&hp.agent);
  }
  release(&hp.lock);
}

// Successful exec is the only activation point. Failed exec keeps the old
// image; any successful replacement consumes or revokes the boot authority.
void
hp_exec(struct proc *p, char *path)
{
  int activate = p->hp_bootstrap && strncmp(path, "/hpagent", 9) == 0;

  hp_detach(p);
  p->hp_authorized = activate;
}

int
hp_agent_next(void)
{
  struct proc *me = myproc();

  acquire(&hp.lock);
  for(;;){
    if(me != hp.agent || me->killed){
      release(&hp.lock);
      return HP_ERR_INVALID;
    }
    if(hp.pending && !hp.pending->delivered)
      break;
    sleep(&hp.agent, &hp.lock);
  }
  hp.pending->delivered = 1;
  release(&hp.lock);
  return 0; // event is now readable in the read-only event page
}

int
hp_agent_decide(void)
{
  struct hp_decision_page reply;

  acquire(&hp.lock);
  if(myproc() != hp.agent || myproc()->killed){
    release(&hp.lock);
    return HP_ERR_INVALID;
  }
  // The sole mapped writer is this single-threaded process, now in kernel
  // mode. Validate a snapshot; never treat the user readiness flag as a lock.
  memmove(&reply, decision, sizeof(reply));
  if(!hp.pending || !hp.pending->delivered || hp.pending->answered ||
     reply.version != HP_ABI_VERSION || reply.ready != 1 ||
     reply.req_id != hp.pending->id ||
     (uint)(ticks - hp.pending->started) >= HP_TIMEOUT_TICKS ||
     reply.action < 0 || reply.action >= HP_NACTION){
    release(&hp.lock);
    return HP_ERR_INVALID;
  }
  hp.pending->action = reply.action;
  hp.pending->answered = 1;
  decision->ready = 0;
  wakeup(&ticks);
  release(&hp.lock);
  return 0;
}

int
hp_submit_request(int syscall_nr, int pid, int arg0, int arg1, int arg2)
{
  struct hp_request req;
  struct proc *me = myproc();
  uint start;
  int result;

  acquire(&hp.lock);
  if(me == hp.agent){
    release(&hp.lock);
    return HP_ERR_INVALID;
  }
  if(!hp.agent){
    release(&hp.lock);
    return HP_ERR_NO_AGENT;
  }
  if(hp.pending){
    release(&hp.lock);
    return HP_ERR_BUSY; // M1 has no implicit queue or unbounded slot wait
  }
  if(!hp.next_id){
    release(&hp.lock);
    return HP_ERR_EXHAUSTED; // never reuse an ID after unsigned wraparound
  }
  memset(&req, 0, sizeof(req));
  req.id = hp.next_id++;
  req.started = ticks;
  hp.pending = &req;
  decision->ready = 0;
  events->event.req_id = req.id;
  events->event.syscall_nr = syscall_nr;
  events->event.pid = pid;
  events->event.arg0 = arg0;
  events->event.arg1 = arg1;
  events->event.arg2 = arg2;
  events->ready = 1;
  wakeup(&hp.agent);
  start = req.started;
  while(!req.answered){
    if(me->killed){
      result = HP_ERR_INTERRUPTED;
      goto done;
    }
    if(!hp.agent){
      result = HP_ERR_NO_AGENT;
      goto done;
    }
    if((uint)(ticks - start) >= HP_TIMEOUT_TICKS){
      result = HP_ERR_TIMEOUT;
      goto done;
    }
    sleep(&ticks, &hp.lock);
  }
  result = req.action;

done:
  hp.pending = 0;
  events->ready = 0;
  decision->ready = 0;
  release(&hp.lock);
  return result;
}
