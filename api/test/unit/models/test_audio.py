import uuid
from unittest import mock

import pytest

from api.models.audio import Audio, AudioAddOn
from test.factory.faker import WaveformProvider


@pytest.fixture
@pytest.mark.django_db
def audio_fixture():
    audio = Audio(
        identifier=uuid.uuid4(),
    )

    audio.save()

    return audio


@pytest.mark.django_db
@mock.patch("api.models.audio.generate_peaks")
def test_audio_waveform_caches(generate_peaks_mock, audio_fixture):
    mock_waveform = WaveformProvider.generate_waveform()
    generate_peaks_mock.return_value = mock_waveform

    assert AudioAddOn.objects.count() == 0
    assert audio_fixture.get_or_create_waveform() == mock_waveform
    assert AudioAddOn.objects.count() == 1
    # Ensure the waveform was saved
    assert (
        AudioAddOn.objects.get(audio_identifier=audio_fixture.identifier).waveform_peaks
        == mock_waveform
    )
    assert audio_fixture.get_or_create_waveform() == mock_waveform
    # Should only be called once if Audio.get_or_create_waveform is using the DB value on subsequent calls
    generate_peaks_mock.assert_called_once()

    # Ensure there are no foreign constraints on the AudioAddOn that would cause failures during refresh
    audio_fixture.delete()

    assert AudioAddOn.objects.count() == 1
