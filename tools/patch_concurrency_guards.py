import os

def patch_ask():
    path = "app/ui/features/ask.js"
    with open(path, "r", encoding="utf-8") as f:
        c = f.read()

    old_fn = '''  async function updateMedia() {
    clearTimeout(mediaTimer);
    mediaTimer = null;'''

    new_fn = '''  let inFlightMedia = false;
  async function updateMedia() {
    if (inFlightMedia) return;
    inFlightMedia = true;
    clearTimeout(mediaTimer);
    mediaTimer = null;'''

    if old_fn in c:
        c = c.replace(old_fn, new_fn, 1)

    old_sched = '''    if (document.contains(main)) {
      const now = Date.now();
      let delay = 3000;
      if (document.hidden || (now - lastInteraction > 60000)) {
        delay = 15000;
      } else if (now < fastPollUntil) {
        delay = 1000;
      } else {
        delay = 3000;
      }
      mediaTimer = setTimeout(updateMedia, delay);
    }
  }'''

    new_sched = '''    inFlightMedia = false;
    if (document.contains(main)) {
      const now = Date.now();
      let delay = 3000;
      if (document.hidden || (now - lastInteraction > 60000)) {
        delay = 15000;
      } else if (now < fastPollUntil) {
        delay = 1000;
      } else {
        delay = 3000;
      }
      mediaTimer = setTimeout(updateMedia, delay);
    }
  }'''

    if old_sched in c:
        c = c.replace(old_sched, new_sched, 1)

    old_render = "if (!mediaTimer && consecutiveErrors < 3) updateMedia();"
    new_render = "if (!mediaTimer && !inFlightMedia && consecutiveErrors < 3) updateMedia();"
    if old_render in c:
        c = c.replace(old_render, new_render, 1)

    with open(path, "w", encoding="utf-8") as f:
        f.write(c)
    print("Patched ask.js with inFlightMedia guard")


def patch_today():
    path = "app/ui/features/today.js"
    with open(path, "r", encoding="utf-8") as f:
        c = f.read()

    old_load = '''let focusTimer = null;

export async function loadToday() {
  set('today', { loading: true });'''

    new_load = '''let focusTimer = null;
let loadTodayInFlight = false;

export async function loadToday() {
  if (loadTodayInFlight) return;
  loadTodayInFlight = true;
  try {
    set('today', { loading: true });'''

    old_set = '''  set('today', {
    loading: false,
    tasks: t.ok ? t.items : [],
    tasksError: t.ok ? null : t,
    reminders: r.ok ? r.items : [],
    notes: n.ok ? n.items : [],
    briefing: store.today?.snoozedBriefing ? null : briefingData,
    events: rawEvents,
    calendarConfigured: isGcalConnected,
    agendaError: c.ok ? null : c,
  });
}'''

    new_set = '''  set('today', {
    loading: false,
    tasks: t.ok ? t.items : [],
    tasksError: t.ok ? null : t,
    reminders: r.ok ? r.items : [],
    notes: n.ok ? n.items : [],
    briefing: store.today?.snoozedBriefing ? null : briefingData,
    events: rawEvents,
    calendarConfigured: isGcalConnected,
    agendaError: c.ok ? null : c,
  });
  } finally {
    loadTodayInFlight = false;
  }
}'''

    if old_load in c and old_set in c:
        c = c.replace(old_load, new_load, 1)
        c = c.replace(old_set, new_set, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(c)
        print("Patched today.js with loadTodayInFlight guard")
    else:
        print("Warning: targets not found in today.js")


if __name__ == "__main__":
    patch_ask()
    patch_today()
