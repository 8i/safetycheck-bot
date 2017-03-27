import os
import time
import threading

from flask import Flask, request, jsonify, Response
from slackclient import SlackClient


# Your bot token
slack_token = os.environ["SC_SLACK_TOKEN"]
# The token/key generated by slack when you create a slash command (Used to verify it's slack instigating things)
slash_command_token = os.environ["SC_SLASH_COMMAND_TOKEN"]


port = int(os.environ.get("SC_PORT", "8080"))
safety_check_text = "It's time to check in @channel. Please add a slack reaction to mark yourself ok!"

check_cool_down = int(os.environ.get("SC_COOL_DOWN", "3600"))

app = Flask(__name__)
sc = SlackClient(slack_token)

checks = {}


def get_users():
    users = sc.api_call(
        "users.list"
    )

    assert users['ok']
    return users[u'members']


@app.route("/safetycheck", methods=["POST"])
def safetycheck():
    if 'token' not in request.form or request.form['token'] != slash_command_token:
        return Response('Token incorrect', 401, {})

    users = get_users()
    user_by_username = {user[u'name']: user for user in users}
    user_by_id = {user[u'id']: user for user in users}

    channel_info = sc.api_call(
        "channels.info",
        channel=request.form['channel_id']
    )

    assert channel_info[u'ok']

    if not channel_info[u'channel'][u'is_member']:
        return jsonify({
            "text": "Safetybot is not a member of this channel, add with \\invite @safetybot",
        })

    # Make sure the old safety check is at least an hour old before overwriting
    if request.form['channel_id'] in checks:
        check = checks[request.form['channel_id']]
        print("Previous check exists from " + str(check['check_message_ts']))
        print("Current time is " + str(time.time()))
        print("Cool down time time is " + str(check_cool_down))
        if int(time.time() - float(check['check_message_ts'])) < check_cool_down:
            return jsonify({
                "text": "Safety check already in progress!",
            })

    # filter channel members that are bots
    members = [m_id for m_id in channel_info[u'channel'][u'members'] if not user_by_id[m_id][u'is_bot']]

    msg_response = sc.api_call(
        "chat.postMessage",
        channel=request.form['channel_id'],
        text=safety_check_text,
        username="safetybot",
        link_names=True,
        attachments=[],
    )
    print msg_response
    check = {
        "user_by_username": user_by_username,
        "user_by_id": user_by_id,
        "channel_id": request.form['channel_id'],
        "checked_in": [],
        "not_checked_in": members,
        "check_message_ts": msg_response[u'message'][u'ts']
    }
    checks[request.form['channel_id']] = check

    return jsonify({
        "text": "Triggered a check in",
    })


def find_check_message(channel_id, last_ts):
    channel_history = sc.api_call(
        "channels.history",
        channel=channel_id,
        oldest=last_ts,
    )
    assert channel_history[u'ok']
    for msg in channel_history[u'messages']:
        if msg[u'type'] == u'message' and msg[u'subtype'] == u'bot_message':
            if msg[u'text'] == safety_check_text:
                return msg[u'ts']
    return None


def process_item(m):
    i = m[u'item']

    if i.get(u'channel') in checks:
        c = checks[i[u'channel']]

        # check that reaction is for the correct message
        if i[u'ts'] != c['check_message_ts']:
            return None

        c['checked_in'].append(m[u'user'])
        try:
            c['not_checked_in'].remove(m[u'user'])
        except ValueError:
            # If someone joins the channel and responds then they won't be in the list.
            pass
        return i[u'channel']
    return None


def create_user_list(c):
    names = sorted(["@" + c['user_by_id'][uu][u'name'] for uu in c['not_checked_in']])
    return ', '.join(names)


def worker():
    import thread

    reaction_types = ['reaction_added']
    thread_sc = SlackClient(slack_token)
    if not thread_sc.rtm_connect():
        print("Connection Failed, invalid token?")
        thread.interrupt_main()
        #raise Exception("Connection Failed, invalid token?")

    while True:
        try:
            messages = thread_sc.rtm_read()
            updated = set()
            for m in messages:
                if m[u'type'] in reaction_types:

                    updated_channel = process_item(m)
                    if updated_channel:
                        updated.add(updated_channel)

            for c_id in updated:
                c = checks[c_id]

                total = len(c['checked_in']) + len(c['not_checked_in'])
                attachments = []

                if len(c['checked_in']) != total:
                    attachments.append({
                        "text": "%d of %d have responded they are ok" % (len(c['checked_in']), len(c['checked_in']) + len(c['not_checked_in']))
                    })
                    attachments.append({
                        "text": "Waiting for %s" % (create_user_list(c)),
                    })
                else:
                    attachments.append({
                        "text": "... but everyone is okay!"
                    })

                chat_update = sc.api_call(
                    "chat.update",
                    channel=c['channel_id'],
                    ts=c['check_message_ts'],
                    text=safety_check_text,
                    link_names=1,
                    attachments=attachments,
                )

                #print "chat_update: ", chat_update
                assert chat_update[u'ok']
        except Exception, e:
            print str(e)

        time.sleep(1)


if __name__ == "__main__":
    import sys

    t = threading.Thread(target=worker)
    try:
        t.start()

        app.run(host='0.0.0.0', port=port)
    except KeyboardInterrupt as e:
        sys.exit(1)

