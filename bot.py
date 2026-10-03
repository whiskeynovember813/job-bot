import os
import random
import asyncio
from datetime import datetime, timedelta

import discord
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
FRIEND_ID = int(os.getenv("FRIEND_ID"))

# Daily active window
START_HOUR = 4    # 4:00 AM
END_HOUR = 23     # 11:00 PM

# Schedule settings
BURSTS_PER_DAY = 4
PINGS_PER_BURST = 5

# Delay between individual mentions
MIN_PING_DELAY = 1
MAX_PING_DELAY = 3

# Minimum time between daily bursts
MIN_BURST_GAP = 60 * 60  # 1 hour


intents = discord.Intents.default()

client = discord.Client(intents=intents)


def generate_times():
    """
    Generate four random times between 4:00 AM and 11:00 PM.
    Times are at least one hour apart.
    """

    now = datetime.now()

    start = now.replace(
        hour=START_HOUR,
        minute=0,
        second=0,
        microsecond=0
    )

    end = now.replace(
        hour=END_HOUR,
        minute=0,
        second=0,
        microsecond=0
    )

    # If the entire window has passed,
    # generate tomorrow's schedule.
    if now >= end:
        start += timedelta(days=1)
        end += timedelta(days=1)

    # Pick random minute positions.
    possible_minutes = int(
        (end - start).total_seconds() / 60
    )

    while True:
        selected_minutes = sorted(
            random.sample(
                range(possible_minutes),
                BURSTS_PER_DAY
            )
        )

        # Make sure every burst is at least
        # one hour away from the next.
        if all(
            selected_minutes[i + 1] - selected_minutes[i]
            >= 60
            for i in range(BURSTS_PER_DAY - 1)
        ):
            break

    return [
        start + timedelta(minutes=minute)
        for minute in selected_minutes
    ]


async def send_pings(friend):
    """
    Send five separate mentions of the target friend.
    """

    mention = f"<@{FRIEND_ID}>"

    print(
        f"\nSending {PINGS_PER_BURST} mentions at "
        f"{datetime.now().strftime('%I:%M:%S %p')}"
    )

    for number in range(1, PINGS_PER_BURST + 1):

        try:
            await friend.send(mention)

            print(
                f"  Sent mention "
                f"{number}/{PINGS_PER_BURST}"
            )

        except discord.Forbidden as error:
            print(
                f"  Discord rejected the DM: {error}"
            )
            return

        except discord.HTTPException as error:
            print(
                f"  Discord HTTP error: {error}"
            )
            return

        except Exception as error:
            print(
                f"  Unexpected error: {error}"
            )
            return

        # Don't wait after the final message.
        if number < PINGS_PER_BURST:
            delay = random.uniform(
                MIN_PING_DELAY,
                MAX_PING_DELAY
            )

            await asyncio.sleep(delay)


async def daily_scheduler():
    """
    Generate and execute a new schedule every day.
    """

    await client.wait_until_ready()

    try:
        friend = await client.fetch_user(FRIEND_ID)
    except Exception as error:
        print(
            f"Could not find the target user: {error}"
        )
        return

    print(f"Target friend: {friend}")

    while not client.is_closed():

        times = generate_times()

        print("\nToday's Job Bot schedule:")

        for number, target_time in enumerate(
            times,
            start=1
        ):
            print(
                f"  Burst {number}: "
                f"{target_time.strftime('%I:%M:%S %p')}"
            )

        print()

        # Go through today's scheduled times.
        for target_time in times:

            seconds_until = (
                target_time - datetime.now()
            ).total_seconds()

            # Skip anything that has already passed.
            if seconds_until <= 0:
                print(
                    f"Skipping "
                    f"{target_time.strftime('%I:%M:%S %p')} "
                    f"(already passed)."
                )
                continue

            print(
                f"Next burst in "
                f"{seconds_until / 3600:.2f} hours."
            )

            await asyncio.sleep(seconds_until)

            await send_pings(friend)

        # Wait until after midnight before
        # generating the next day's schedule.
        now = datetime.now()

        tomorrow = (
            now + timedelta(days=1)
        ).replace(
            hour=0,
            minute=0,
            second=5,
            microsecond=0
        )

        seconds_until_tomorrow = (
            tomorrow - datetime.now()
        ).total_seconds()

        print(
            "\nToday's schedule is finished."
        )

        print(
            f"Generating tomorrow's schedule in "
            f"{seconds_until_tomorrow / 3600:.2f} hours."
        )

        await asyncio.sleep(
            max(seconds_until_tomorrow, 1)
        )


@client.event
async def on_ready():

    print(
        f"Job Bot is online as {client.user}"
    )

    # Only start one scheduler.
    if not hasattr(
        client,
        "scheduler_started"
    ):

        client.scheduler_started = True

        asyncio.create_task(
            daily_scheduler()
        )


if not TOKEN:
    print(
        "ERROR: DISCORD_TOKEN is missing "
        "from your .env file."
    )
    raise SystemExit


if not FRIEND_ID:
    print(
        "ERROR: FRIEND_ID is missing "
        "from your .env file."
    )
    raise SystemExit


client.run(TOKEN)