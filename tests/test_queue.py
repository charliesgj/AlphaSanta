import asyncio
from dataclasses import dataclass
from typing import List

from alphasanta.orchestrator import SantaQueue, SantaTask
from alphasanta.schema import UserLetter, SantaDecision


@dataclass
class StubSanta:
    decisions: List[str]

    async def process_letter(self, letter: UserLetter, alpha_signal=None):
        verdict = self.decisions.pop(0)
        return SantaDecision(verdict=verdict, publish=False, meta={}, source=letter.source)

    async def process_alpha_only(self, letter: UserLetter, alpha_signal=None):
        verdict = self.decisions.pop(0)
        return SantaDecision(verdict=verdict, publish=False, meta={}, source=letter.source)


async def collect_results(task: SantaTask, decision: SantaDecision, bucket: List[str]):
    bucket.append(decision.verdict)


def test_queue_preserves_fifo_order():
    results: List[str] = []

    async def callback(task, decision):
        await collect_results(task, decision, results)

    async def run_test():
        santa = StubSanta(decisions=["first", "second"])
        queue = SantaQueue(santa_agent=santa, result_callback=callback)
        await queue.start()
        letter = UserLetter(token="A", thesis="", source="community")
        await queue.enqueue_letter(letter)
        await queue.enqueue_alpha(UserLetter(token="B", thesis="", source="alpha"))
        await queue.join()
        await queue.stop()

    asyncio.run(run_test())
    assert results == ["first", "second"]
