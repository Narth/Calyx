#!/usr/bin/env python3
"""
Fix emoji encoding issues in demo script
"""

import re

def fix_emojis():
    # Read the file
    with open('demo_teaching_system.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace emojis with ASCII equivalents
    replacements = {
        '🔧': '[INIT]',
        '✅': '[OK]',
        '⚠️': '[WARN]',
        '❌': '[ERROR]',
        '🎯': '[DEMO]',
        '📚': '[SESSION]',
        '📊': '[METRICS]',
        '🔍': '[PATTERN]',
        '🚀': '[SIM]',
        '🤝': '[INTEGRATION]',
        '📝': '[RECORD]',
        '🔄': '[TRANSFER]',
        '🧠': '[ADAPTIVE]',
        '⚙️': '[PARAMS]',
        '📜': '[HISTORY]',
        '📋': '[REPORT]',
        '💾': '[SAVE]',
        '🎬': '[START]',
        '🎉': '[COMPLETE]',
        '📖': '[DOCS]'
    }

    for emoji, replacement in replacements.items():
        content = content.replace(emoji, replacement)

    # Write back
    with open('demo_teaching_system.py', 'w', encoding='utf-8') as f:
        f.write(content)

    print('Emojis replaced successfully')

if __name__ == "__main__":
    fix_emojis()
