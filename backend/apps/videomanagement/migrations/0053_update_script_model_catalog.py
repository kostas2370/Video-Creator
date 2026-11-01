from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("videomanagement", "0052_move_usage_to_own_app"),
    ]

    operations = [
        migrations.AlterField(
            model_name="templateprompt",
            name="gpt_model",
            field=models.CharField(
                blank=True,
                choices=[
                    ("gpt-3.5-turbo", "gpt-3.5-turbo"),
                    ("gpt-4", "gpt-4"),
                    ("gpt-4-turbo", "gpt-4-turbo"),
                    ("gpt-4o", "gpt-4o"),
                    ("gpt-4o-mini", "gpt-4o-mini"),
                    ("gpt-4.1", "gpt-4.1"),
                    ("gpt-4.1-mini", "gpt-4.1-mini"),
                    ("gpt-4.1-nano", "gpt-4.1-nano"),
                    ("gpt-5", "gpt-5"),
                    ("gpt-5-mini", "gpt-5-mini"),
                    ("gpt-5-nano", "gpt-5-nano"),
                    ("gpt-5-chat-latest", "gpt-5-chat-latest"),
                    ("gpt-5.1", "gpt-5.1"),
                    ("gpt-5.1-chat-latest", "gpt-5.1-chat-latest"),
                    ("gpt-5.2", "gpt-5.2"),
                    ("gpt-5.2-chat-latest", "gpt-5.2-chat-latest"),
                    ("gpt-5.3-chat-latest", "gpt-5.3-chat-latest"),
                    ("gpt-5.4", "gpt-5.4"),
                    ("gpt-5.4-mini", "gpt-5.4-mini"),
                    ("gpt-5.4-nano", "gpt-5.4-nano"),
                    ("gpt-5.5", "gpt-5.5"),
                    ("gpt-5.6-luna", "gpt-5.6-luna"),
                    ("gpt-5.6-sol", "gpt-5.6-sol"),
                    ("gpt-5.6-terra", "gpt-5.6-terra"),
                    ("gpt-6-astra", "gpt-6-astra"),
                    ("o1", "o1"),
                    ("o3", "o3"),
                    ("o3-mini", "o3-mini"),
                    ("o4-mini", "o4-mini"),
                    ("claude-sonnet-4-6", "claude-sonnet-4-6"),
                    ("gemini-4-argon", "gemini-4-argon"),
                    ("gemini-3.8-flash", "gemini-3.8-flash"),
                    ("gemini-3.5-flash-lite", "gemini-3.5-flash-lite"),
                ],
                default="gpt-5.4-mini",
                max_length=50,
            ),
        ),
    ]
