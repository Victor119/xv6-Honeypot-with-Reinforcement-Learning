// hptrigger.c - Milestone 1 test client for the honeypot channel.
//
// Sends a synthetic request through the control channel and prints the action
// the agent (or the timeout fallback) returned.  This stands in for the real
// syscall_dispatcher of Milestone 2 so the M1 round-trip can be exercised
// from the shell.
//
// Usage:
//   hptrigger <syscall_nr> [arg0]
//
// Demonstrations:
// Init starts the agent. Negative transport results are reported separately
// from policy actions; future enforcement must use BLOCK for these failures.

#include "types.h"
#include "user.h"
#include "honeypot.h"

static char *actname[HP_NACTION] = { "BLOCK", "ALLOW", "RESTRICT" };

int
main(int argc, char *argv[])
{
  int nr, arg0 = 0, action;

  if(argc < 2){
    printf(1, "usage: hptrigger <syscall_nr> [arg0]\n");
    exit();
  }
  nr = atoi(argv[1]);
  if(argc >= 3)
    arg0 = atoi(argv[2]);

  action = hp_trigger(nr, arg0);
  if(action < 0){
    printf(1, "hptrigger: nr=%d -> transport=%d fallback=BLOCK\n", nr, action);
    exit();
  }
  if(action >= HP_NACTION){
    printf(1, "hptrigger: invalid action %d\n", action);
    exit();
  }
  printf(1, "hptrigger: nr=%d arg0=%d -> %s\n", nr, arg0, actname[action]);
  exit();
}
