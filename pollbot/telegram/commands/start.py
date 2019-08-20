"""The start command handler."""
import time
from uuid import UUID
from telegram.ext import run_async

from pollbot.i18n import i18n
from pollbot.models import Poll
from pollbot.helper.enums import ExpectedInput, StartAction
from pollbot.helper.session import session_wrapper
from pollbot.helper.text import split_text
from pollbot.display import compile_poll_text
from pollbot.telegram.keyboard import get_main_keyboard
from pollbot.telegram.keyboard.external import get_external_add_option_keyboard


@run_async
@session_wrapper()
def start(bot, update, session, user):
    """Send a start text."""
    # Truncate the /start command
    text = update.message.text[6:].strip()
    user.started = True

    try:
        poll_uuid = UUID(text.split('-')[0])
        action = StartAction(int(text.split('-')[1]))

        poll = session.query(Poll).filter(Poll.uuid == poll_uuid).one()
    except:
        text = ''

    main_keyboard = get_main_keyboard()
    # We got an empty text, just send the start message
    if text == '':
        update.message.chat.send_message(
            i18n.t('misc.start', locale=user.locale),
            parse_mode='markdown',
            reply_markup=main_keyboard,
            disable_web_page_preview=True,
        )

        return

    if poll is None:
        return 'This poll no longer exists.'

    if action == StartAction.new_option:
        # Update the expected input and set the current poll
        user.expected_input = ExpectedInput.new_user_option.name
        user.current_poll = poll
        session.commit()

        update.message.chat.send_message(
            i18n.t('creation.option.first', locale=poll.locale),
            parse_mode='markdown',
            reply_markup=get_external_add_option_keyboard(poll)
        )
    elif action == StartAction.show_results:
        # Get all lines of the poll
        lines = compile_poll_text(session, poll)
        # Now split the text into chunks of max 4000 characters
        chunks = split_text(lines)

        for chunk in chunks:
            message = '\n'.join(chunk)
            try:
                update.message.chat.send_message(
                    message,
                    parse_mode='markdown',
                    disable_web_page_preview=True,
                )
            # Retry for Timeout error (happens quite often when sending large messages)
            except TimeoutError:
                update.message.chat.send_message(
                    message,
                    parse_mode='markdown',
                    disable_web_page_preview=True,
                )
            time.sleep(1)

        update.message.chat.send_message(
            i18n.t('misc.start_after_results', locale=poll.locale),
            parse_mode='markdown',
            reply_markup=main_keyboard,
        )
