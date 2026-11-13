"""Quick commands should fire on commands, and ordinary sentences should reach the AI."""

import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _isolation  # noqa: E402,F401  Before anything from the app: a throwaway profile.

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

import command_intent  # noqa: E402

CONVERSATION = """
close the door behind you is an idiom, what does it mean
open a new chapter in my life, any advice
open source licenses explained
open questions about black holes
play it safe or take risks?
play devil's advocate on this idea
remember when we talked about taxes
remember to breathe, why do people say that
remind me what a monad is
remind me how recursion works
save the world movies, recommend some
volume of a sphere formula
task management tips
add a task to my thesis outline section, how should I structure it
what time is the world cup final
news about the stock market explained
dns explained simply
ping pong rules
decode the meaning of this poem
what is a port in networking
how do I set an alarm in python
why is the sky blue?
what's the difference between tcp and udp
should I learn rust or go
how do I restart my computer
why is my code slow
should I clean my laptop
""".strip().splitlines()

COMMANDS = """
open notepad
open chrome
open downloads
open youtube.com
close chrome
play hotel california
play lofi on spotify
pause
next song
volume 50
set volume to 30
mute
add task buy milk
new task call the bank
remind me to call mom in 10 minutes
remind me at 5pm to stretch
remember that my router password is on the fridge
remember the spare key is in the blue box
save note: check the invoice
note that the meeting moved to friday
what time is it
what time is it?
what's the time
what is the date
what's the weather?
weather
weather in london
news
news about india
ping google.com
dns google.com
battery
system status
take a screenshot
what is my ip
explain my clipboard
what's on my screen
summarize my notes
what's on my calendar today
wifi password Home
list wifi
check my wifi
lock my pc
confirm
cancel
add task explain the budget to sam
new task how to file taxes
remind me to ask john why in 10 minutes
remember that why is a good question
""".strip().splitlines()


class Intent(unittest.TestCase):
    def test_ordinary_sentences_go_to_the_ai(self):
        wrong = [s for s in CONVERSATION if not command_intent.is_conversation(s)]
        self.assertEqual(wrong, [])

    def test_real_commands_still_fire(self):
        wrong = [s for s in COMMANDS if command_intent.is_conversation(s)]
        self.assertEqual(wrong, [])

    def test_empty_text_is_not_conversation(self):
        self.assertFalse(command_intent.is_conversation(""))


class PingTarget(unittest.TestCase):
    def test_only_real_hosts_count(self):
        for host in ("google.com", "8.8.8.8", "localhost", "::1"):
            self.assertTrue(command_intent.looks_like_host(host), host)
        for word in ("pong", "rules", "me", "the"):
            self.assertFalse(command_intent.looks_like_host(word), word)


if __name__ == "__main__":
    unittest.main()
