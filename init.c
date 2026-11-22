// init: The initial user-level program

#include "types.h"
#include "stat.h"
#include "user.h"
#include "fcntl.h"

char *argv[] = { "sh", 0 };

static void
startagent(void)
{
  int ready[2], pid, fd, n = 0, i;
  char fdstr[12], reversed[12], result;
  char *agentargv[] = { "hpagent", fdstr, 0 };

  if(pipe(ready) < 0){
    printf(1, "init: agent pipe failed\n");
    return;
  }
  fd = ready[1];
  do {
    reversed[n++] = '0' + fd % 10;
    fd /= 10;
  } while(fd);
  for(i = 0; i < n; i++)
    fdstr[i] = reversed[n-i-1];
  fdstr[n] = 0;

  pid = hp_start();
  if(pid == 0){
    close(ready[0]);
    exec("/hpagent", agentargv);
    printf(1, "init: exec hpagent failed\n");
    exit();
  }
  close(ready[1]);
  if(pid < 0 || read(ready[0], &result, 1) != 1 || result != '1')
    printf(1, "init: agent unavailable; reboot to recover\n");
  close(ready[0]);
}

int
main(void)
{
  int pid, wpid;

  if(open("console", O_RDWR) < 0){
    mknod("console", 1, 1);
    open("console", O_RDWR);
  }
  dup(0);  // stdout
  dup(0);  // stderr

  // Register the designated agent before any attacker shell can run.
  startagent();

  for(;;){
    printf(1, "init: starting sh\n");
    pid = fork();
    if(pid < 0){
      printf(1, "init: fork failed\n");
      exit();
    }
    if(pid == 0){
      exec("sh", argv);
      printf(1, "init: exec sh failed\n");
      exit();
    }
    while((wpid=wait()) >= 0 && wpid != pid)
      ; // Quietly reap the agent and orphaned children while the shell runs.
  }
}
