from dotenv import load_dotenv
from flask import flash, Flask, render_template, request, redirect, url_for
from flask_limiter import Limiter
from kasa import SmartDeviceException, SmartPlug
import asyncio
import os
import time
import logging
import sys

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# Configure handler to write to stdout
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.INFO)

# Create a logging format
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
stdout_handler.setFormatter(formatter)

# Set the logger to use the stdout handler
app.logger.addHandler(stdout_handler)
app.logger.setLevel(logging.INFO)

limiter = Limiter(app, default_limits=["1 per 30 seconds"])

last_toggle_on_timestamp = 0
last_toggle_off_timestamp = 0
logger = app.logger


async def toggle_plug_with_retry(state):
    global last_toggle_on_timestamp
    global last_toggle_off_timestamp
    retries = 5
    for i in range(retries):
        try:
            # Check for rate limiting
            current_time = time.time()
            if (
                current_time - max(last_toggle_off_timestamp, last_toggle_on_timestamp)
                < 2
            ):
                logger.info("Spam detected. Rate limiting.")
                flash("Please do not spam the button")
                return

            plug = SmartPlug(os.getenv("LIGHT_IP_ADDRESS"))
            await plug.update()  # Get the current state
            logger.info(plug.state_information)
            if state == "on" and plug.is_off:
                if current_time - last_toggle_on_timestamp < 30:
                    logger.info("Preventing turn on")
                    flash("Please dont turn on the lights so frequently")
                    return
                logger.info("turning on")
                await plug.turn_on()
                last_toggle_on_timestamp = current_time
            elif state == "off" and plug.is_on:
                logger.info("turning off")
                await plug.turn_off()
                last_toggle_off_timestamp = current_time
            return
        except SmartDeviceException as e:
            if "Unable to query the device" in str(e) and i < retries - 1:
                logger.info(f"Retry {i + 1}/{retries}: {e}")
                await asyncio.sleep(1)  # Wait for 1 second before retrying
            else:
                raise


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/toggle", methods=["POST"])
@limiter.limit(
    "1 per 30 seconds", error_message="Rate limit exceeded."
)  # Customize error message
def toggle():
    state = request.form.get("state")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(toggle_plug_with_retry(state))
    except Exception as e:
        flash(str(e))  # Flash the exception message
    finally:
        loop.close()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=False)

# TODO:
# make an endpoint for getting the emeter electricity usage this month
# make a link to sponsorship page on github to tip me
