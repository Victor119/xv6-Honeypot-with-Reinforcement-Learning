// M1 control syscalls. Page access never grants authority by itself.
#include "types.h"
#include "x86.h"
#include "defs.h"
#include "param.h"
#include "memlayout.h"
#include "mmu.h"
#include "proc.h"
#include "honeypot.h"

int
sys_hp_start(void)
{
  return hp_start_agent();
}

int
sys_hp_register(void)
{
  return hp_register_agent();
}

int
sys_hp_next(void)
{
  return hp_agent_next();
}

int
sys_hp_decide(void)
{
  return hp_agent_decide();
}

// Synthetic only: returns an action or an explicit negative transport status.
// M2 must remove/gate this injector and mediate selected real operations.
int
sys_hp_trigger(void)
{
  int nr, arg0;

  if(argint(0, &nr) < 0 || argint(1, &arg0) < 0)
    return HP_ERR_INVALID;
  return hp_submit_request(nr, myproc()->pid, arg0, 0, 0);
}
