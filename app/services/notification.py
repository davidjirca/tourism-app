import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from twilio.rest import Client

from app.core.config import settings
from app.websockets.notifications import connected_clients

# Initialize Twilio client
twilio_client = Client(settings.TWILIO_SID, settings.TWILIO_AUTH_TOKEN)


def send_email_alert(user_email, destination, old_price, new_price):
    """Send an email notification for a price drop."""
    subject = f"🔥 Price Drop Alert: {destination}!"
    body = f"""
    Great news! The flight price for {destination} has dropped!

    🏷️ **Previous Price:** ${old_price}
    💰 **New Price:** ${new_price}

    Hurry, book now before prices go up! ✈️
    """

    msg = MIMEMultipart()
    msg["From"] = settings.EMAIL_SENDER
    msg["To"] = user_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
        server.starttls()
        server.login(settings.EMAIL_SENDER, settings.EMAIL_PASSWORD)
        server.sendmail(settings.EMAIL_SENDER, user_email, msg.as_string())
        server.quit()
        print(f"✅ Email sent to {user_email} for {destination}")
        return True
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        return False


def send_sms_alert(user_phone, destination, old_price, new_price):
    """Send an SMS notification for a price drop."""
    try:
        message = twilio_client.messages.create(
            body=f"🔥 Flight to {destination} just dropped from ${old_price} to ${new_price}! Book now!",
            from_=settings.TWILIO_PHONE_NUMBER,
            to=user_phone
        )
        print(f"✅ SMS sent to {user_phone}: {message.sid}")
        return True
    except Exception as e:
        print(f"❌ Error sending SMS: {e}")
        return False


def send_push_notification(destination, old_price, new_price):
    """Send a push notification for a price drop through WebSockets."""
    notification_data = json.dumps({
        "type": "price_drop",
        "destination": destination,
        "old_price": old_price,
        "new_price": new_price,
        "message": f"Price drop alert! {destination} is now ${new_price}!"
    })

    success_count = 0
    for client in connected_clients:
        try:
            client.send_text(notification_data)
            success_count += 1
        except Exception as e:
            print(f"❌ Error sending WebSocket notification: {e}")

    return success_count > 0