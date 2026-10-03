import os
import random
from datetime import datetime, timedelta, timezone

import discord

TOKEN = os.environ["DISCORD_TOKEN"]
FRIEND_ID = int(os.environ["FRIEND_ID"])

START_HOUR = 4
END_HOUR = 23

BURSTS_PER_DAY = 4
PINGS_PER_BURST = 5


def generate_schedule(day):
    """Generate four deterministic random times for a particular day."""

    seed = int(day.strftime("%Y%m%d"))
    rng = random.Random(seed)

    start_minutes = START_HOUR * 60
    end_minutes = END_HOUR * 60

    while True:
        minutes = sorted(
            rng.sample(
                range(start_minutes, end_minutes),
                BURSTS_PER_DAY
            )
        )

        if all(
            minutes[i + 1] - minutes[i] >= 60
            for i in range(BURSTS_PER_DAY - 1)
        ):
            return minutes


def get_current_time():
    """Return current UTC time."""

    return datetime.now(timezone.utc)


async def send_mentions():
    """Log in, DM the friend five times, then disconnect."""

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

            print("Burst complete.")

        except discord.Forbidden as error:
            print(f"Discord rejected the DM: {error}")

        except discord.HTTPException as error:
            print(f"Discord HTTP error: {error}")

        except Exception as error:
            print(f"Unexpected error: {error}")

        finally:
            await client.close()

    await client.start(TOKEN)


def main():
    now = get_current_time()

    # Convert UTC to Chicago time.
    # GitHub Actions runs in UTC, while your desired
    # schedule is based on Chicago local time.
    import zoneinfo

    chicago = zoneinfo.ZoneInfo("America/Chicago")
    local_now = now.astimezone(chicago)

    today = local_now.date()

    schedule = generate_schedule(today)

    print(
        f"Today's Job Bot schedule "
        f"({local_now.strftime('%Y-%m-%d')} Chicago time):"
    )

    for number, minutes in enumerate(schedule, start=1):
        hour = minutes // 60
        minute = minutes % 60

        print(
            f"  Burst {number}: "
            f"{hour:02d}:{minute:02d}"
        )

    current_minutes = (
        local_now.hour * 60
        + local_now.minute
    )

    # GitHub will run this workflow every five minutes.
    # Find out whether the current five-minute window
    # contains one of today's scheduled times.
    for burst_number, scheduled_minutes in enumerate(
        schedule,
        start=1
    ):
        if (
            scheduled_minutes
            <= current_minutes
            < scheduled_minutes + 5
        ):
            print(
                f"Burst {burst_number} is due now."
            )

            import asyncio
            asyncio.run(send_mentions())

            return

    print("No burst is due right now.")


if __name__ == "__main__":
    main()
