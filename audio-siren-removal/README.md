# Siren removal and enhancement

Removes a sweeping siren from `input/Recording_14.m4a` while keeping door sounds and radio chatter, then boosts the quiet parts.

```
./process.sh input/Recording_14.m4a output
```

- `remove_siren.py`: tracks the siren's pitch (760–1420 Hz) frame by frame and cuts it and its overtones down to the surrounding noise floor, in several passes at different resolutions. It only runs where the siren is active.
- `denoise.py`: gentle hiss reduction using the quietest 2 seconds as the noise profile.
- `process.sh`: runs both, then high-pass filter, presence EQ, dynamic normalisation and a limiter.

Outputs: `*_siren_removed_enhanced.m4a` (main) and `*_siren_removed_only.m4a` (original levels).
