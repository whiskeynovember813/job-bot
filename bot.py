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

STATE_FILE = "jobbot_state.txt"

CHICAGO = ZoneInfo("America/Chicago")


def generate_schedule(day):
    """Generate the same four random times for the same date."""

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
    hour = minutes // 60
    minute = minutes % 60

    suffix = "AM"

    if hour >= 12:
        suffix = "PM"

    display_hour = hour % 12

    if display_hour == 0:
        display_hour = 12

    return f"{display_hour}:{minute:02d} {suffix}"


def load_state():
    if not os.path.exists(STATE_FILE):
        return None

    try:
        with open(STATE_FILE, "r") as file:
            return file.read().strip()
    except Exception:
        return None


def save_state(date_string, burst_number):
    with open(STATE_FILE, "w") as file:
        file.write(f"{date_string}|{burst_number}\n")


async def send_pings():
    """Log into Discord and send five mentions."""

    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    success = False

    @client.event
    async def on_ready():
        nonlocal success

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

                if number < PINGS_PER_BURST:
                    await asyncio.sleep(
                        random.uniform(1, 3)
                    )

            print("Burst complete.")

            success = True

        except discord.Forbidden as error:
            print(f"Discord rejected the DM: {error}")

        except discord.HTTPException as error:
            print(f"Discord HTTP error: {error}")

        except Exception as error:
            print(f"Unexpected error: {error}")

        finally:
            await client.close()

    await client.start(TOKEN)

    return success


def main():

    now_utc = datetime.now(timezone.utc)
    now_chicago = now_utc.astimezone(CHICAGO)

    today = now_chicago.date()
    date_string = today.isoformat()

    current_minutes = (
        now_chicago.hour * 60
        + now_chicago.minute
    )

    schedule = generate_schedule(today)

    print(
        f"Today's Job Bot schedule "
        f"({date_string} Chicago time):"
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

    state = load_state()

    if state:
        print(f"\nLast successful burst: {state}")
    else:
        print("\nNo burst has been recorded yet today.")

    # Find the latest scheduled burst that has already
    # happened today.
    latest_due = None

    for number, scheduled_time in enumerate(
        schedule,
        start=1
    ):
        if scheduled_time <= current_minutes:
            latest_due = (
                number,
                scheduled_time
            )

    if latest_due is None:
        print("\nNo burst is due yet.")
        return

    burst_number, scheduled_time = latest_due

    # If this exact burst was already sent, do nothing.
    if state == f"{date_string}|{burst_number}":
        print(
            f"\nBurst {burst_number} was already sent today."
        )
        return

    print(
        f"\nBurst {burst_number} is due!"
    )

    print(
        f"Scheduled time: "
        f"{format_time(scheduled_time)}"
    )

    print("\nSending five mentions...")

    success = asyncio.run(send_pings())

    if success:
        save_state(date_string, burst_number)

        print(
            f"Recorded Burst {burst_number} as sent."
        )
    else:
        print(
            "Burst was not recorded because "
            "the DM attempt failed."
        )


if __name__ == "__main__":
    main()
