# SafetyBot

If there is an emergency, let your team mark themselves safe by adding
reactions to a bot's slack message.

## Usage

Create a custom integration for your team, you'll need a bot and a
slash command. Then launch with docker:

```
docker run -d \
    -e SC_SLACK_TOKEN=YOUR_BOT_TOKEN \
    -e SC_SLASH_COMMAND_TOKEN=YOUR_SLASH_COMMAND_TOKEN \
    -p 80:8080 \
    quay.io/joel/safetybot
```

Assuming you've called the slash command "safetycheck" and the bot
is called "safetybot":

```
/invite safetybot
/safetycheck
```

Then you'll get a message asking people in the channel to check in,
and safetybot will update the message attachments with who has yet
to check in by adding a reaction.

Obviously, if a user removes their reaction, they are still counted.
If they add multiple reactions they are only counted once, etc.
