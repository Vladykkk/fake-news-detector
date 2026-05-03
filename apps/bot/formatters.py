"""Форматування результатів аналізу для Telegram (HTML)."""


class ResultFormatter:
    """Клас для форматування результатів аналізу."""

    VERDICT_EMOJI = {
        'safe': '\u2705',
        'suspicious': '\u26a0\ufe0f',
        'ipso': '\U0001f6a8',
    }

    VERDICT_LABEL = {
        'safe': 'Безпечно',
        'suspicious': 'Підозрілий',
        'ipso': 'ІПСО виявлено',
    }

    @classmethod
    def format(cls, result) -> str:
        """Форматувати AnalysisResult у HTML-повідомлення для Telegram."""
        emoji = cls.VERDICT_EMOJI.get(result.verdict, '\u2753')
        label = cls.VERDICT_LABEL.get(result.verdict, 'Невідомо')
        score_pct = int(result.final_score * 100)

        filled = score_pct // 10
        bar = '\u2588' * filled + '\u2591' * (10 - filled)

        lines = [
            f"{emoji} <b>Результат аналізу: {label}</b>",
            "",
            f"\U0001f4ca Загальний бал: <b>{score_pct}%</b>",
            f"[{bar}]",
            "",
            "\U0001f4dd Деталі:",
            f"  \u2022 Наративи: {int(result.narrative_score * 100)}%",
            f"  \u2022 Риторика: {int(result.rhetoric_score * 100)}%",
            f"  \u2022 Подібність: {int(result.similarity_score * 100)}%",
        ]

        if result.detected_narratives:
            lines.append("")
            lines.append("\U0001f50d Виявлені наративи:")
            for narr in result.detected_narratives[:3]:
                conf = int(narr.get('confidence', 0) * 100)
                lines.append(f"  \u2022 {narr.get('label', '?')} ({conf}%)")

        if result.detected_rhetoric:
            lines.append("")
            lines.append("\U0001f3af Маніпулятивні техніки:")
            for rhet in result.detected_rhetoric[:3]:
                lines.append(f"  \u2022 {rhet.get('type', '?')}")

        lines.extend([
            "",
            f"\u23f1 Час аналізу: {result.processing_time_ms} мс",
            f"\U0001f310 Мова: {result.detected_language}",
        ])

        return "\n".join(lines)


def format_result_message(result) -> str:
    """Зворотна сумісність — делегує до ResultFormatter."""
    return ResultFormatter.format(result)
