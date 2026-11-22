// hpagent.c - Milestone 1 user-space test agent for the honeypot channel.
//
// This is the skeleton of the "native C agent" described in the proposal.
// In M1 it does NOT run a trained RL policy; it registers on the control
// channel and applies a small, transparent FIXED test policy so the full
// request/reply path can be demonstrated end-to-end.  Milestone 4 swaps the
// fixed rule for the imported policy while keeping this loop unchanged.
//
// Started by init before the shell; manual copies cannot claim the agent role.

#include "types.h"
#include "user.h"
#include "honeypot.h"
#ifdef HP_TESTING
#include "honeypot_test.h"
#endif

// The agent writes replies through its dedicated decision-page mapping.
static volatile struct hp_decision_page *decision = (void*)HP_DECISION_VA;

static int
reply(uint id, int action)
{
  decision->version = HP_ABI_VERSION;
  decision->req_id = id;
  decision->action = action;
  __sync_synchronize();
  decision->ready = 1;
  return hp_decide();
}

#ifdef HP_TESTING
static void
check(int ok, char *name)
{
  if(!ok){
    hp_test_log("hpagent: FAIL ", name);
    exit();
  }
}

// These fault injections exist only in the acceptance image. They do not
// classify real commands and must not become part of the M2 policy interface.
static int
test_event(struct hp_event *ev)
{
  int fds[2], pid;
  char marker;
  char *args[] = { "hptest", "revoked", 0 };

  switch(ev->syscall_nr){
  case HP_TEST_REPLIES:
    decision->version = HP_ABI_VERSION + 1;
    decision->req_id = ev->req_id;
    decision->action = HP_ALLOW;
    decision->ready = 1;
    check(hp_decide() == HP_ERR_INVALID, "ABI rejection");
    decision->version = HP_ABI_VERSION;
    decision->ready = 0;
    check(hp_decide() == HP_ERR_INVALID, "readiness rejection");
    check(reply(ev->req_id - 1, HP_ALLOW) == HP_ERR_INVALID, "stale rejection");
    check(reply(ev->req_id, HP_NACTION) == HP_ERR_INVALID, "action rejection");
    check(reply(ev->req_id, HP_ALLOW) == 0, "valid reply");
    check(reply(ev->req_id, HP_ALLOW) == HP_ERR_INVALID, "duplicate rejection");
    hp_test_log("hpagent: PASS ", "reply validation");
    return 1;
  case HP_TEST_DELAY:
    sleep(HP_TIMEOUT_TICKS + 20);
    check(reply(ev->req_id, HP_ALLOW) == HP_ERR_INVALID, "late rejection");
    hp_test_log("hpagent: PASS ", "late reply rejection");
    return 1;
  case HP_TEST_EXIT:
    exit();
  case HP_TEST_EXEC:
    exec("/hptest", args);
    check(0, "exec replacement");
    return 1;
  case HP_TEST_RDONLY:
    *(volatile uint*)HP_EVENT_VA = 0;
    check(0, "read-only event page");
    return 1;
  case HP_TEST_FORK:
    check(exec("/missing-agent-test", args) == -1, "failed exec");
    check(hp_register() == 0, "authority retained after failed exec");
    check(pipe(fds) == 0, "fork pipe");
    pid = fork();
    check(pid >= 0, "agent fork");
    if(pid == 0){
      close(fds[0]);
      if(hp_register() != HP_ERR_INVALID || hp_next() != HP_ERR_INVALID ||
         hp_decide() != HP_ERR_INVALID){
        write(fds[1], "x", 1);
        exit();
      }
      write(fds[1], "s", 1);
      // A child must not even be able to read the agent's decision mapping.
      marker = *(volatile char*)HP_DECISION_VA;
      write(fds[1], &marker, 1);
      exit();
    }
    close(fds[1]);
    check(read(fds[0], &marker, 1) == 1 && marker == 's', "fork authority");
    check(read(fds[0], &marker, 1) == 0, "fork page isolation");
    close(fds[0]);
    wait();
    check(reply(ev->req_id, HP_ALLOW) == 0, "parent authority retained");
    hp_test_log("hpagent: PASS ", "fork isolation");
    return 1;
  }
  return 0;
}
#endif

// Fixed test policy for M1: a placeholder stand-in for the RL policy.
// The mapping is intentionally simple and readable so demos are predictable:
//   syscall_nr <  0        -> BLOCK      (malformed / sentinel)
//   syscall_nr == 0        -> ALLOW      (benign no-op)
//   syscall_nr even        -> RESTRICT   (allow with caution)
//   syscall_nr odd         -> BLOCK      (treated as destructive)
static int
fixed_policy(struct hp_event *ev)
{
  if(ev->syscall_nr < 0)
    return HP_BLOCK;
  if(ev->syscall_nr == 0)
    return HP_ALLOW;
  if((ev->syscall_nr % 2) == 0)
    return HP_RESTRICT;
  return HP_BLOCK;
}

int
main(int argc, char *argv[])
{
  struct hp_event ev;
  volatile struct hp_event_page *events = (void*)HP_EVENT_VA;
  int action;

  if(hp_register() < 0){
    printf(1, "hpagent: registration denied\n");
    exit();
  }
  printf(1, "hpagent: registered, waiting for events (fixed test policy)\n");
#ifdef HP_TESTING
  check(hp_register() == 0, "idempotent registration");
#endif
  if(argc == 2){
    write(atoi(argv[1]), "1", 1);
    close(atoi(argv[1]));
  }

  for(;;){
    if(hp_next() < 0){
      printf(1, "hpagent: hp_next failed (not the agent or killed)\n");
      exit();
    }
    if(events->version != HP_ABI_VERSION){
      printf(1, "hpagent: invalid event page\n");
      exit();
    }
    if(events->ready != 1)
      continue; // the requester may have timed out before this process ran
    ev = events->event;
#ifdef HP_TESTING
    if(test_event(&ev))
      continue;
#endif
    action = fixed_policy(&ev);
    if(reply(ev.req_id, action) < 0)
      printf(1, "hpagent: hp_decide rejected (stale req %d?)\n", ev.req_id);
  }
}
