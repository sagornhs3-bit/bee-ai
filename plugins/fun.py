"""Fun plugin - English jokes, stories, compliments"""

import random

JOKES = [
    "Why don't scientists trust atoms? Because they make up everything!",
    "I told my wife she was drawing her eyebrows too high. She looked surprised.",
    "Why did the scarecrow win an award? Because he was outstanding in his field!",
    "I'm reading a book about anti-gravity. It's impossible to put down!",
    "What do you call a fake noodle? An impasta!",
    "Why don't skeletons fight each other? They don't have the guts.",
    "I used to hate facial hair, but then it grew on me.",
    "Why did the coffee file a police report? It got mugged!",
    "What's the best thing about Switzerland? I don't know, but the flag is a big plus.",
    "Parallel lines have so much in common. It's a shame they'll never meet.",
    "Why did the math book look sad? Because it had too many problems.",
    "I'm on a seafood diet. I see food and I eat it.",
]

COMPLIMENTS = [
    "You're absolutely amazing!",
    "People like you make the world brighter.",
    "You're smarter than you give yourself credit for!",
    "Your smile is genuinely beautiful!",
    "You're doing great - keep going!",
    "The world is better with you in it.",
    "You have a kind heart - that's rare.",
    "I love talking with you.",
    "You're stronger than you think!",
    "You make everything better.",
]

STORIES = [
    "Once there was a small girl named Lily. Every day she walked to school past a big old tree. One morning she found a tiny injured bird beneath it. She took it home and cared for it. A week later, the bird was healthy again. One sunrise, the bird gave Lily a small golden key before flying away. The key opened an old wooden box - inside was a magic pencil. Whatever she wrote came true. Lily learned: kindness always comes back.",

    "In a small village lived a greedy merchant. He cheated everyone for money. One day a monk came asking for alms. The merchant refused. The monk smiled: 'Then let me leave you with this - never hide what you cannot bear to lose.' The merchant didn't understand. The next day his house was robbed. Everything gone. Only then did he realize - what's in your heart is the only true wealth.",

    "A small boy once went to the market with his mother. They saw a beggar shivering in the cold. The boy said, 'Mom, can I give him my coat?' She asked, 'Won't you be cold?' He replied, 'I have another one at home. He doesn't.' His mother wept. That day, the boy learned - the joy of giving is unmatched.",
]

POEMS = [
    "The road not taken calls my name,\nThrough autumn leaves and gentle rain,\nA choice once made, a life once led,\nStill echoes in the things unsaid.",

    "Stars above in silver light,\nWhisper secrets through the night,\nDreams that dance on moonlit streams,\nCarry hope through waking dreams.",

    "Raindrops drum on rooftops old,\nStories that the thunder told,\nPetrichor and quiet grace,\nPeace found in a rainy place.",
]

DARE_QUESTIONS = [
    "Be honest - what's the last thing that made you truly laugh?",
    "What's the most embarrassing moment of your life?",
    "Tell me - how many times did you check your phone today?",
    "What's your biggest dream?",
    "If you could meet anyone, living or dead, who would it be?",
]


def get_joke() -> str:
    return random.choice(JOKES)


def get_compliment() -> str:
    return random.choice(COMPLIMENTS)


def get_story() -> str:
    return random.choice(STORIES)


def get_poem() -> str:
    return random.choice(POEMS)


def get_dare() -> str:
    return random.choice(DARE_QUESTIONS)


def get_antakshari() -> str:
    return "I'll start! 'Twinkle twinkle little star, how I wonder what you are...' Now you continue with a song starting with 'S'!"