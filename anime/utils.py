import datetime
import re

def get_midnights():
    now = datetime.datetime.now()
    last_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)   
    next_midnight = last_midnight + datetime.timedelta(days=1)
    last_midnight_epoch = int(last_midnight.timestamp())
    next_midnight_epoch = int(next_midnight.timestamp())

    return last_midnight_epoch, next_midnight_epoch

def html_to_discord(text):
    formatting_map = {
        'b': '**',
        'strong': '**',
        'i': '*',
        'em': '*',
        'u': '__',
        's': '~~',
        'code': '`',
    }

    def replace_tag(match):
        tag = match.group(1).lower()
        content = match.group(2)
        
        if tag in formatting_map:
            return f"{formatting_map[tag]}{content}{formatting_map[tag]}"
        elif tag == 'pre':
            return f"```\n{content}\n```"
        else:
            return match.group(0)

    text = re.sub(r'<([a-zA-Z]+)>(.*?)</\1>', replace_tag, text, flags=re.DOTALL)

    text = text.replace('<br>', '\n')
    text = re.sub(r'<a href="(.*?)">(.*?)</a>', r'[\2](\1)', text)
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text