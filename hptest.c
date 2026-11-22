// Guest acceptance tests: assertions exercise the real syscall and VM paths.
#include "types.h"
#include "user.h"
#include "honeypot.h"
#include "honeypot_test.h"

static void
check(int ok, char *name)
{
  if(!ok){
    hp_test_log("hptest: FAIL ", name);
    exit();
  }
}

static void
unauthorized(void)
{
  check(hp_start() == HP_ERR_INVALID, "init-only bootstrap");
  check(hp_register() == HP_ERR_INVALID, "registration denied");
  check(hp_next() == HP_ERR_INVALID, "event fetch denied");
  check(hp_decide() == HP_ERR_INVALID, "forged reply denied");
}

// A pipe proves the child reached the access and did not reach the next write.
// xv6 has no exit status; merely waiting for a child would not prove a fault.
static void
unmapped(uint address)
{
  int fds[2], pid;
  char marker;

  check(pipe(fds) == 0, "isolation pipe");
  pid = fork();
  check(pid >= 0, "isolation fork");
  if(pid == 0){
    close(fds[0]);
    write(fds[1], "s", 1);
    marker = *(volatile char*)address;
    write(fds[1], &marker, 1);
    exit();
  }
  close(fds[1]);
  check(read(fds[0], &marker, 1) == 1 && marker == 's', "probe started");
  check(read(fds[0], &marker, 1) == 0, "page must be unmapped");
  close(fds[0]);
  wait();
}

static void
slot_reuse(void)
{
  int i, pid, fds[2];
  char marker;
  for(i = 0; i < 64; i++){
    check(pipe(fds) == 0, "reuse pipe");
    pid = fork();
    check(pid >= 0, "reuse fork");
    if(pid == 0){
      close(fds[0]);
      unauthorized();
      write(fds[1], "1", 1);
      exit();
    }
    close(fds[1]);
    check(read(fds[0], &marker, 1) == 1 && marker == '1', "reuse authority");
    close(fds[0]);
    check(wait() == pid, "reuse wait");
  }
}

#ifdef HP_TESTING
static void
contended(int interrupt)
{
  int pid, fds[2];
  char marker;

  check(pipe(fds) == 0, "contention pipe");
  pid = fork();
  check(pid >= 0, "contention fork");
  if(pid == 0){
    close(fds[0]);
    write(fds[1], "s", 1);
    check(hp_trigger(HP_TEST_DELAY, 0) == HP_ERR_TIMEOUT, "owner timeout");
    write(fds[1], "t", 1);
    exit();
  }
  close(fds[1]);
  check(read(fds[0], &marker, 1) == 1, "owner started");
  sleep(10);
  check(hp_trigger(0, 0) == HP_ERR_BUSY, "busy status");
  if(interrupt){
    check(kill(pid) == 0, "kill requester");
    check(read(fds[0], &marker, 1) == 0, "killed requester exits");
  } else {
    check(read(fds[0], &marker, 1) == 1 && marker == 't', "owner completes");
  }
  close(fds[0]);
  check(wait() == pid, "owner reaped");
  sleep(HP_TIMEOUT_TICKS + 30);
  check(hp_trigger(0, 0) == HP_ALLOW, "channel recovers");
}
#endif

int
main(int argc, char *argv[])
{
  int i;
  uint size;
  char *mode = argc > 1 ? argv[1] : "basic";
#ifdef HP_TESTING
  int started;
#endif

  unauthorized();
  if(strcmp(mode, "basic") == 0){
    size = (uint)sbrk(0);
    check(sbrk(HP_EVENT_VA - size) == (char*)-1, "reserved heap boundary");
    check((uint)sbrk(0) == size, "heap unchanged after rejection");
    unmapped(HP_EVENT_VA);
    unmapped(HP_DECISION_VA);
    check(hp_trigger(0, 0) == HP_ALLOW, "allow");
    check(hp_trigger(3, 0) == HP_BLOCK, "block");
    check(hp_trigger(4, 0) == HP_RESTRICT, "restrict");
    slot_reuse();
  } else if(strcmp(mode, "stress") == 0){
    for(i = 0; i < 1000; i++)
      check(hp_trigger(0, i) == HP_ALLOW, "1000 exchanges");
  } else if(strcmp(mode, "absent") == 0 || strcmp(mode, "revoked") == 0){
    check(hp_trigger(0, 0) == HP_ERR_NO_AGENT, "agent unavailable");
    unmapped(HP_EVENT_VA);
    unmapped(HP_DECISION_VA);
    slot_reuse();
#ifdef HP_TESTING
  } else if(strcmp(mode, "replies") == 0){
    check(hp_trigger(HP_TEST_REPLIES, 0) == HP_ALLOW, "reply validation");
  } else if(strcmp(mode, "timeout") == 0){
    started = uptime();
    check(hp_trigger(HP_TEST_DELAY, 0) == HP_ERR_TIMEOUT, "timeout status");
    check(uptime() - started >= HP_TIMEOUT_TICKS, "timeout deadline");
    check(uptime() - started < HP_TIMEOUT_TICKS + 30, "bounded timeout");
    sleep(50);
    check(hp_trigger(0, 0) == HP_ALLOW, "timeout recovery");
  } else if(strcmp(mode, "busy") == 0){
    contended(0);
  } else if(strcmp(mode, "interrupted") == 0){
    contended(1);
  } else if(strcmp(mode, "agentfork") == 0){
    check(hp_trigger(HP_TEST_FORK, 0) == HP_ALLOW, "agent fork");
  } else if(strcmp(mode, "exit") == 0){
    check(hp_trigger(HP_TEST_EXIT, 0) == HP_ERR_NO_AGENT, "agent exit");
  } else if(strcmp(mode, "exec") == 0){
    check(hp_trigger(HP_TEST_EXEC, 0) == HP_ERR_NO_AGENT, "agent exec");
  } else if(strcmp(mode, "readonly") == 0){
    check(hp_trigger(HP_TEST_RDONLY, 0) == HP_ERR_NO_AGENT, "event write faults");
#endif
  } else {
    check(0, "unknown mode or HP_TESTING disabled");
  }
  hp_test_log("hptest: PASS ", mode);
  exit();
}
