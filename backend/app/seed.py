"""Populate the database with realistic demo data.

Usage (from the backend/ directory):

    python -m app.seed          # add demo data, keeping anything already there
    python -m app.seed --reset  # drop every table first

Every demo account uses the password: password123
"""

import argparse
import random

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import GroupMembership, Note, Rating, StudyGroup, User
from app.security import hash_password

DEMO_PASSWORD = "password123"

USERS = [
    ("ada@wisc.edu", "ada_l", "CS + math double major. I take way too many notes."),
    ("grace@wisc.edu", "graceh", "Compilers TA. Ask me about debugging."),
    ("linus@wisc.edu", "linus_t", "Systems person. Lives in the Linux man pages."),
    ("katherine@wisc.edu", "kjohnson", "Numerical methods and anything orbital."),
    ("alan@wisc.edu", "alan_t", "Theory of computation enjoyer."),
]

NOTES = [
    (
        "CS 400 — Red-black tree rotations, worked through",
        "Every rotation case drawn out, plus the four insert fixup cases. The trick that "
        "finally made it click for me: only recolor when the uncle is red, otherwise "
        "rotate. Includes the two exam problems from last spring with full solutions.",
        "CS400",
        ["data-structures", "exam-prep", "trees"],
    ),
    (
        "CS 537 — Midterm 1 review sheet (processes, scheduling, memory)",
        "Condensed six lectures into three pages. Covers fork/exec semantics, the "
        "difference between MLFQ and lottery scheduling, and a page table walkthrough "
        "for a 32-bit two-level scheme.",
        "CS537",
        ["operating-systems", "exam-prep"],
    ),
    (
        "CS 240 — Induction proof templates",
        "The five proof shapes that show up on every homework: weak induction, strong "
        "induction, structural induction, pigeonhole, and contradiction. Each one has a "
        "fill-in-the-blank skeleton followed by a solved example.",
        "CS240",
        ["discrete-math", "proofs"],
    ),
    (
        "CS 300 — Java collections cheat sheet",
        "ArrayList vs LinkedList vs HashMap, when each one is actually the right call, "
        "and the Big-O for every operation you'll be asked about. Also the iterator "
        "gotcha that breaks half of the P2 submissions.",
        "CS300",
        ["java", "cheatsheet", "data-structures"],
    ),
    (
        "CS 577 — Dynamic programming recipe",
        "A repeatable process for DP problems: define the subproblem in English first, "
        "then the recurrence, then the base case, then the order of evaluation. Applied "
        "to LIS, edit distance, knapsack and interval scheduling.",
        "CS577",
        ["algorithms", "dynamic-programming"],
    ),
    (
        "CS 220 — Pandas groupby, finally explained",
        "split-apply-combine with actual pictures. Covers groupby().agg(), the "
        "difference between transform and apply, and why your merge produced 40,000 "
        "rows when you expected 400.",
        "CS220",
        ["python", "data-science", "pandas"],
    ),
    (
        "CS 407 — Buffer overflow lab notes",
        "How to reason about the stack frame layout before you write a single byte of "
        "payload. Includes the gdb commands I use every time and a diagram of where the "
        "saved return address sits.",
        "CS407",
        ["security", "systems"],
    ),
    (
        "CS 540 — Neural net backprop by hand",
        "One tiny two-layer network, every partial derivative computed by hand, matched "
        "against PyTorch's autograd output so you can check yourself. The chain rule is "
        "the whole thing.",
        "CS540",
        ["machine-learning", "math"],
    ),
]

GROUPS = [
    (
        "CS 400 Sunday problem sets",
        "We meet in College Library and work through the week's problem set together. "
        "Bring your own attempt first — we compare approaches rather than copy.",
        "CS400",
        "Sundays 2-4pm",
        "College Library, 3rd floor",
        6,
    ),
    (
        "OS midterm cram crew",
        "Two weeks of focused review before the CS 537 midterm. Whiteboard-heavy.",
        "CS537",
        "Tue/Thu 7pm",
        "CS building 1240",
        8,
    ),
    (
        "Algorithms interview prep",
        "Half the session is course material, half is LeetCode-style mock interviews. "
        "Good for anyone recruiting for summer internships.",
        "CS577",
        "Saturdays 10am",
        "Union South, Northwoods room",
        10,
    ),
    (
        "Intro to ML reading group",
        "We read one paper or one textbook chapter a week and take turns presenting.",
        "CS540",
        "Wednesdays 5pm",
        "Zoom (link in group chat)",
        12,
    ),
]

RATING_COMMENTS = [
    "This is better than the lecture slides, honestly.",
    "Saved me hours before the exam. Thank you.",
    "Good notes, but the last section skips a step or two.",
    "Clear explanations. The worked examples are the best part.",
    "Solid. Would love a few more practice problems.",
    "Exactly what I needed the night before the midterm.",
    "Helpful, though it assumes you already did the reading.",
]


def seed(reset: bool = False) -> None:
    if reset:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    random.seed(7)  # deterministic demo data
    db = SessionLocal()
    try:
        if db.scalar(select(User).limit(1)) is not None and not reset:
            print("Database already has data. Re-run with --reset to start over.")
            return

        users = [
            User(
                email=email,
                username=username,
                bio=bio,
                hashed_password=hash_password(DEMO_PASSWORD),
            )
            for email, username, bio in USERS
        ]
        db.add_all(users)
        db.flush()

        notes = []
        for index, (title, content, course, tags) in enumerate(NOTES):
            note = Note(
                title=title,
                content=content,
                course_code=course,
                tags=",".join(tags),
                author_id=users[index % len(users)].id,
            )
            notes.append(note)
        db.add_all(notes)
        db.flush()

        for note in notes:
            raters = [user for user in users if user.id != note.author_id]
            for rater in random.sample(raters, k=random.randint(1, len(raters))):
                db.add(
                    Rating(
                        note_id=note.id,
                        user_id=rater.id,
                        score=random.choice([3, 4, 4, 5, 5, 5]),
                        comment=random.choice(RATING_COMMENTS),
                    )
                )

        for index, (name, description, course, when, where, capacity) in enumerate(GROUPS):
            owner = users[index % len(users)]
            group = StudyGroup(
                name=name,
                description=description,
                course_code=course,
                meeting_time=when,
                location=where,
                capacity=capacity,
                owner_id=owner.id,
            )
            group.memberships.append(GroupMembership(user_id=owner.id))
            others = [user for user in users if user.id != owner.id]
            for member in random.sample(others, k=random.randint(1, min(3, len(others)))):
                group.memberships.append(GroupMembership(user_id=member.id))
            db.add(group)

        db.commit()
        print(
            f"Seeded {len(users)} users, {len(notes)} notes and {len(GROUPS)} study groups.\n"
            f"Sign in as any of: {', '.join(email for email, _, _ in USERS)}\n"
            f"Password for all demo accounts: {DEMO_PASSWORD}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the StudyHub database with demo data.")
    parser.add_argument("--reset", action="store_true", help="drop all tables first")
    seed(reset=parser.parse_args().reset)
