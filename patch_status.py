import re

def main():
    with open('app/ui/state/status.js', 'r', encoding='utf-8') as f:
        content = f.read()

    # tick()
    old_tick = """async function tick() {
  if (document.hidden) return schedule();
  if (inflight) return;
  inflight = system.status();"""
    new_tick = """async function tick() {
  if (inflight) return;
  inflight = system.status(document.hidden);"""

    if old_tick in content:
        content = content.replace(old_tick, new_tick)
    else:
        print("Could not find tick() logic in status.js")

    # interval()
    old_interval = """function interval() {
  if (!store.online) return OFFLINE_MS;"""
    new_interval = """function interval() {
  if (document.hidden) return 30000;
  if (!store.online) return OFFLINE_MS;"""

    if old_interval in content:
        content = content.replace(old_interval, new_interval)
    else:
        print("Could not find interval() in status.js")

    # schedule()
    old_schedule = """function schedule() {
  clearTimeout(timer);
  if (document.hidden) return;
  timer = setTimeout(tick, interval());
}"""
    new_schedule = """function schedule() {
  clearTimeout(timer);
  timer = setTimeout(tick, interval());
}"""

    if old_schedule in content:
        content = content.replace(old_schedule, new_schedule)
    else:
        print("Could not find schedule() in status.js")

    # startStatus()
    old_start = """export function startStatus() {
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) clearTimeout(timer);
    else tick();
  });"""
    new_start = """export function startStatus() {
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) { clearTimeout(timer); tick(); }
  });"""

    if old_start in content:
        content = content.replace(old_start, new_start)
    else:
        print("Could not find startStatus() in status.js")

    with open('app/ui/state/status.js', 'w', encoding='utf-8') as f:
        f.write(content)
    print("status.js patched.")

if __name__ == "__main__":
    main()
