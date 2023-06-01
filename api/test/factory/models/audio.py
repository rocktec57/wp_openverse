from test.factory.faker import Faker
from test.factory.models.media import IdentifierFactory, MediaFactory

import factory
from factory.django import DjangoModelFactory

from api.models.audio import Audio, AudioAddOn, MatureAudio


class MatureAudioFactory(DjangoModelFactory):
    class Meta:
        model = MatureAudio

    media_obj = factory.SubFactory("test.factory.models.audio.AudioFactory")


class AudioFactory(MediaFactory):
    _mature_factory = MatureAudioFactory

    class Meta:
        model = Audio


class AudioAddOnFactory(DjangoModelFactory):
    class Meta:
        model = AudioAddOn

    audio_identifier = IdentifierFactory(AudioFactory)

    waveform_peaks = Faker("waveform")
