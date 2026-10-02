# Sample audio

`sample.wav` and `sample.pcm` contain the same 4.275-second utterance:

> A cold lucid indifference reigned in his soul.

Source: LibriSpeech `test-clean`, utterance `1089-134686-0007`, distributed by
[OpenSLR SLR12](https://www.openslr.org/12) under CC BY 4.0.

The original 16 kHz FLAC was converted to 24 kHz mono signed PCM16. The WAV is
used by upload examples; the headerless PCM is streamed by the Python and
Node.js realtime examples.
