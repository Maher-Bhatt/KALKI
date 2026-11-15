# KALKI reel · how to post it

A 16-second, 9:16 edit made from the real app. Every cut lands on a beat at **120 BPM**
(one beat every 0.5 s), and the drop is at **0:02**.

| File | Use it when |
|---|---|
| `kalki_reel_beat.mp4` | You want to post right now. It has an original beat and sound effects, so there are no copyright problems. |
| `kalki_reel_sfx.mp4` | You want a **trending sound**. Only the whooshes, hits and typing are in it; you add the song in Instagram. |
| `kalki_reel_silent.mp4` | You edit in CapCut or Instagram's editor and want no audio at all. |
| `kalki_reel_cover.png` | The Reel cover (the "POV: your PC finally talks back" frame). |

## Timeline
| Time | What happens |
|---|---|
| 0:00 to 0:02 | **Hook:** "POV: / your PC / finally / talks back 🗣️", one word per beat |
| 0:02 | **Drop:** flash and a punch-in on the voice orb, "just say HEY KALKI" |
| 0:04 | "and it TALKS BACK" (voice mode replying) |
| 0:05 to 0:09 | **The roast:** "bro you're kinda useless ngl" and KALKI fires back 💀 |
| 0:09 to 0:13 | Eight fast cuts, one per beat: plans your day, calendar, tasks, music, notes, security, screen time, any AI |
| 0:13 | Zoom out: "ALL IN ONE APP" (a snare roll builds) |
| 0:14 | **Logo hit:** KALKI, "Free AI assistant for Windows", "Link in bio 🔗" |

## Adding a trending sound (Instagram)
1. Open Instagram, tap **+**, then **Reel**, and pick `kalki_reel_sfx.mp4`.
2. Tap **Audio** (the music note). In the list, sounds with a small **↗ arrow** are trending right now.
   Pick one with a strong beat drop: phonk, a hard trap beat or a sped-up song all suit this edit.
3. **Line up the drop:** drag the song's start so its drop hits exactly at **0:02**, the white flash.
   If you tap along to the song and it's about **2 taps per second**, the beat matches every cut
   (120 BPM; 60 or 240 BPM also fit).
4. Tap **Volume**: song about 80 to 100%, original audio (the sound effects) about 25 to 35%.
5. Use `kalki_reel_cover.png` as the cover.

Instagram's audio library is licensed for Reels, which is why the song is added there and not
baked into the file. Songs put into the video file itself usually get the Reel muted or blocked.

**TikTok / YouTube Shorts:** same idea. Upload `kalki_reel_sfx.mp4`, tap **Add sound**, pick a
trending sound and set its drop to 0:02.

## Caption
> my PC talks back now and it has zero chill 💀
>
> KALKI is a free AI assistant for Windows. Say "Hey KALKI" and just talk: it plans your day,
> plays your music, opens your apps and roasts you if you're rude.
>
> link in bio 🔗
>
> #ai #aiassistant #windows11 #pcsetup #techtok #productivity #jarvis #coding #techreels #fyp

Optional comment-bait version: change the last line to "comment **KALKI** and I'll DM you the
link". Comments push a Reel further, but you then have to reply to everyone.

## Posting tips for reach
- **Post between 7 and 10 PM** on a weekday, when your followers are most active (check Insights).
- **Pin a comment** with the link or "what should I make it roast next? 👇" to start replies.
- **Reply to every comment in the first hour.** That's when Instagram decides whether to push it.
- **Share it to your Story** with a "new" sticker right after posting.
- Post it as a **Trial Reel** first if your account has that option: it's shown to non-followers
  first, so you can see whether it takes off before it reaches your followers.
- Nothing can guarantee a Reel goes viral, but a 1-second hook, a beat-synced edit, a funny
  moment and a loop-friendly ending are what the algorithm rewards most.

## Rebuild it
`python tools/marketing/make_reel.py` (see `tools/marketing/README.md`). The roast text, captions
and cut list are at the top of the script.
