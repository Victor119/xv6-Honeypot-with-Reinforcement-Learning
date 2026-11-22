// Synthetic fault-injection events, enabled only in HP_TESTING builds.
#define HP_TEST_REPLIES 10001
#define HP_TEST_DELAY   10002
#define HP_TEST_EXIT    10003
#define HP_TEST_EXEC    10004
#define HP_TEST_RDONLY  10005
#define HP_TEST_FORK    10006

// xv6 printf writes one character per syscall. Publish a complete status in
// one console write so another CPU/process cannot split PASS or FAIL markers.
static void
hp_test_log(const char *prefix, const char *detail)
{
  char line[128];
  char overflow[] = "hptest: FAIL status too long\n";
  uint n = strlen(prefix), m = strlen(detail);

  if(n >= sizeof(line) || m >= sizeof(line) - n){
    write(1, overflow, sizeof(overflow) - 1);
    exit();
  }
  memmove(line, prefix, n);
  memmove(line + n, detail, m);
  line[n + m] = '\n';
  write(1, line, n + m + 1);
}
