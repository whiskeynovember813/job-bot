import os
import random
import asyncio
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import discord


TOKEN = os.environ["DISCORD_TOKEN"]
FRIEND_ID = int(os.environ["FRIEND_ID"])

START_HOUR = 4
END_HOUR = 23

BURSTS_PER_DAY = 4
PINGS_PER_BURST = 5

# How late a GitHub Actions run can be and still
# consider a scheduled burst "due".
MAX_LATE_MINUTES = 15

CHICAGO = ZoneInfo("America/Chicago")


def generate_schedule(day):
    """
    Generate four deterministic random times for this date.

    Using the date as the random seed means every GitHub
    Actions run on the same day gets the exact same schedule.
    """

    seed = int(day.strftime("%Y%m%d"))
    rng = random.Random(seed)

    start_minute = START_HOUR * 60
    end_minute = END_HOUR * 60

    while True:
        times = sorted(
            rng.sample(
                range(start_minute, end_minute),
                BURSTS_PER_DAY
            )
        )

        if all(
            times[i + 1] - times[i] >= 60
            for i in range(BURSTS_PER_DAY - 1)
        ):
            return times


def format_time(minutes):
    """Convert minutes after midnight to a readable time."""

    hour = minutes // 60
    minute = minutes % 60

    suffix = "AM"

    if hour >= 12:
        suffix = "PM"

    display_hour = hour % 12

    if display_hour == 0:
        display_hour = 12

    return f"{display_hour}:{minute:02d} {suffix}"


async def send_pings():
    """Log into Discord and send five mentions."""

    intents = discord.Intents.default()

    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"Job Bot is online as {client.user}")

        try:
            friend = await client.fetch_user(FRIEND_ID)

            print(f"Target friend: {friend}")

            mention = f"<@{FRIEND_ID}>"

            for number in range(1, PINGS_PER_BURST + 1):

                await friend.send(mention)

                print(
                    f"Sent mention "
                    f"{number}/{PINGS_PER_BURST}"
                )

                # Short random delay between mentions.
                if number < PINGS_PER_BURST:
                    await asyncio.sleep(
                        random.uniform(1, 3)
                    )

            print("Burst complete.")

        except discord.Forbidden as error:
            print(
                f"Discord rejected the DM: {error}"
            )

        except discord.HTTPException as error:
            print(
                f"Discord HTTP error: {error}"
            )

        except Exception as error:
            print(
                f"Unexpected error: {error}"
            )

        finally:
            await client.close()

    await client.start(TOKEN)


def main():

    now_utc = datetime.now(timezone.utc)
    now_chicago = now_utc.astimezone(CHICAGO)

    today = now_chicago.date()

    current_minutes = (
        now_chicago.hour * 60
        + now_chicago.minute
    )

    schedule = generate_schedule(today)

    print(
        f"Today's Job Bot schedule "
        f"({today} Chicago time):"
    )

    for number, scheduled_time in enumerate(
        schedule,
        start=1
    ):
        print(
            f"  Burst {number}: "
            f"{format_time(scheduled_time)}"
        )

    print(
        f"\nCurrent Chicago time: "
        f"{now_chicago.strftime('%I:%M:%S %p')}"
    )

    # Find a burst that is currently due or was missed
    # by up to MAX_LATE_MINUTES.
    due_burst = None

    for number, scheduled_time in enumerate(
        schedule,
        start=1
    ):

        difference = (
            current_minutes - scheduled_time
        )

        if 0 <= difference <= MAX_LATE_MINUTES:
            due_burst = (
                number,
                scheduled_time
            )
            break

    if due_burst is None:
        print("\nNo burst is due right now.")
        return

    number, scheduled_time = due_burst

    print(
        f"\nBurst {number} is due!"
    )

    print(
        f"Scheduled time: "
        f"{format_time(scheduled_time)}"
    )

    print(
        "Sending five mentions..."
    )

    asyncio.run(send_pings())


if __name__ == "__main__":
    main()
