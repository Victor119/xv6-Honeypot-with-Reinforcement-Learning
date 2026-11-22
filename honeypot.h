// Versioned M1 ABI. Requests are synthetic until M2 adds syscall mediation.
#ifndef XV6_HONEYPOT_H
#define XV6_HONEYPOT_H

#define HP_ABI_VERSION 1
#define HP_BLOCK       0
#define HP_ALLOW       1
#define HP_RESTRICT    2
#define HP_NACTION     3
#define HP_FALLBACK    HP_BLOCK
#define HP_TIMEOUT_TICKS 100

// Transport failures are distinct from a policy BLOCK decision.
#define HP_ERR_INVALID     -1
#define HP_ERR_NO_AGENT    -2
#define HP_ERR_BUSY        -3
#define HP_ERR_TIMEOUT     -4
#define HP_ERR_INTERRUPTED -5
#define HP_ERR_EXHAUSTED   -6

// Reserved outside the normal text/stack/heap range, below KERNBASE.
#define HP_EVENT_VA    0x7fffe000U
#define HP_DECISION_VA 0x7ffff000U

struct hp_event {
  unsigned int req_id;
  int syscall_nr;
  int pid;
  int arg0, arg1, arg2;
};

struct hp_event_page {
  unsigned int version;
  unsigned int ready;
  struct hp_event event;
};

struct hp_decision_page {
  unsigned int version;
  unsigned int req_id;
  int action;
  unsigned int ready;
};

#endif
