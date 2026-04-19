from ._base import run_applescript, escape


def whatsapp_message(contact: str, message: str) -> dict:
    c, m = escape(contact), escape(message)
    r = run_applescript(f'''
tell application "WhatsApp" to activate
delay 1.5
tell application "System Events"
    tell process "WhatsApp"
        keystroke "k" using command down
        delay 0.8
        keystroke "{c}"
        delay 1.8
        key code 125
        delay 0.3
        key code 36
        delay 0.8
        keystroke "{m}"
        delay 0.3
        key code 36
    end tell
end tell''')
    return {
        "label": f"WhatsApp → {contact}",
        "status": "sent" if r["ok"] else "failed",
        "detail": r["err"] or f"Message sent to {contact}",
    }


def imessage(contact: str, message: str) -> dict:
    c, m = escape(contact), escape(message)
    r = run_applescript(f'''
tell application "Messages"
    activate
    set targetBuddy to buddy "{c}" of (first service whose service type = iMessage)
    send "{m}" to targetBuddy
end tell''')
    return {
        "label": f"iMessage → {contact}",
        "status": "sent" if r["ok"] else "failed",
        "detail": r["err"] or f"iMessage sent to {contact}",
    }


def create_note(title: str, body: str = "") -> dict:
    from ._base import ok, fail
    t, b = escape(title), escape(body)
    r = run_applescript(
        f'tell application "Notes" to activate\n'
        f'tell application "Notes" to make new note with properties '
        f'{{name:"{t}", body:"{b}"}}'
    )
    return ok(f'Note: "{title}"', f'Created "{title}"') if r["ok"] else fail("Note", r["err"])


def compose_email(to: str, subject: str, body: str) -> dict:
    from ._base import ok, fail
    t, s, b = escape(to), escape(subject), escape(body)
    r = run_applescript(f'''
tell application "Mail"
    activate
    set msg to make new outgoing message with properties {{subject:"{s}", content:"{b}", visible:true}}
    tell msg to make new to recipient with properties {{address:"{t}"}}
end tell''')
    return ok(f"Email to {to}", "Draft ready") if r["ok"] else fail("Email", r["err"])


def create_reminder(title: str, notes: str = "") -> dict:
    from ._base import ok, fail
    t, n = escape(title), escape(notes)
    r = run_applescript(f'''
tell application "Reminders"
    activate
    tell list "Reminders" to make new reminder with properties {{name:"{t}", body:"{n}"}}
end tell''')
    return ok(f'Reminder: "{title}"', f'Created "{title}"') if r["ok"] else fail("Reminder", r["err"])
