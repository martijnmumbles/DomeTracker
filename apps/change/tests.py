from django.test import TestCase
from apps.change.models import Change
from apps.summoner.models import Summoner


class TestChangeStr(TestCase):
    def test_str(self):
        summoner = Summoner.objects.create(
            name="TestPlayer",
            summoner_id="sum123",
            account_id="acc123",
            puu_id="puu_change_str",
        )
        change = Change.objects.last()
        result = str(change)
        self.assertIn("Action", result)
        self.assertIn("ID:", result)
        self.assertIn("Created at:", result)


class TestChangeSignalCreation(TestCase):
    def test_change_created_on_summoner_save(self):
        initial_count = Change.objects.count()
        Summoner.objects.create(
            name="TestPlayer",
            summoner_id="sum123",
            account_id="acc123",
            puu_id="puu_change_signal",
        )
        self.assertEqual(Change.objects.count(), initial_count + 1)

    def test_change_records_new_object(self):
        summoner = Summoner.objects.create(
            name="TestPlayer",
            summoner_id="sum123",
            account_id="acc123",
            puu_id="puu_change_new",
        )
        change = Change.objects.last()
        self.assertIsNotNone(change.new_object)
        self.assertEqual(change.new_object["name"], "TestPlayer")

    def test_change_tracks_modifications(self):
        summoner = Summoner.objects.create(
            name="Original",
            summoner_id="sum123",
            account_id="acc123",
            puu_id="puu_change_mod",
        )
        summoner.name = "Updated"
        summoner.save()

        latest_change = Change.objects.last()
        self.assertEqual(latest_change.new_object["name"], "Updated")

    def test_change_linked_to_content_type(self):
        summoner = Summoner.objects.create(
            name="TestPlayer",
            summoner_id="sum123",
            account_id="acc123",
            puu_id="puu_change_ct",
        )
        change = Change.objects.last()
        self.assertIsNotNone(change.content_type)
        self.assertEqual(change.object_id, summoner.pk)
