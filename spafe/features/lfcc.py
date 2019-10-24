"""
based on http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.63.8029&rep=rep1&type=pdf
"""
import numpy as np
from ..utils.spectral import rfft, dct
from ..utils.cepstral import cms, cmvn, lifter_ceps
from ..fbanks.linear_fbanks import linear_filter_banks
from ..utils.exceptions import ParameterError, ErrorMsgs
from ..utils.preprocessing import pre_emphasis, framing, windowing, zero_handling


def lfcc(sig,
         fs=16000,
         num_ceps=13,
         nfilts=26,
         nfft=512,
         lifter=22,
         low_freq=None,
         high_freq=None,
         dct_type=2,
         use_cmp=True,
         win_type="hamming",
         win_len=0.025,
         win_hop=0.01,
         pre_emph=0,
         pre_emph_coeff=0.97,
         normalize=1,
         dither=1,
         sum_power=1,
         band_width=1,
         broaden=0,
         use_energy=False):
    """
    Compute the linear-frequency cepstral coefﬁcients (GFCC features) from an audio signal.

    Args:
        sig            (array) : a mono audio signal (Nx1) from which to compute features.
        fs               (int) : the sampling frequency of the signal we are working with.
                                 Default is 16000.
        num_ceps       (float) : number of cepstra to return.
                                 Default is 13.
        nfilts           (int) : the number of filters in the filterbank.
                                 Default is 40.
        nfft             (int) : number of FFT points.
                                 Default is 512.
        win_type       (float) : window type to apply for the windowing.
                                 Default is hamming.
        win_len        (float) : window length in sec.
                                 Default is 0.025.
        win_hop        (float) : step between successive windows in sec.
                                 Default is 0.01.
        pre_emph         (int) : apply pre-emphasis if 1.
                                 Default is 1.
        pre_emph_coeff (float) : apply pre-emphasis filter [1 -pre_emph] (0 = none).
                                 Default is 0.97.
        dither           (int) : 1 = add offset to spectrum as if dither noise.
                                 Default is 0.
        low_freq         (int) : lowest band edge of mel filters (Hz).
                                 Default is 0.
        high_freq        (int) : highest band edge of mel filters (Hz).
                                 Default is samplerate / 2 = 8000.
        lifter           (int) : apply liftering if value > 0.
                                 Default is 22.
        normalize        (int) : apply normalization if 1.
                                 Default is 0.
        bwidth         (float) : width of aud spec filters relative to default.
                                 Default is 1.0.
        dct_type         (int) : type of DCT used - 1 or 2 (or 3 for HTK or 4 for feac).
                                 Default is 2.
        use_cmp          (int) : apply equal-loudness weighting and cube-root compr.
                                 Default is 0.
        broaden          (int) : flag to retain the (useless?) first and last bands
                                 Default is 0.
        use_energy       (int) : overwrite C0 with true log energy
                                 Default is 0.

    Returns:
        (array) : 2d array of LFCC features (num_frames x num_ceps)
    """
    # init freqs
    high_freq = high_freq or fs / 2
    low_freq = low_freq or 0

    # run checks
    if low_freq < 0:
        raise ParameterError(ErrorMsgs["low_freq"])
    if high_freq > (fs / 2):
        raise ParameterError(ErrorMsgs["high_freq"])

    # pre-emphasis
    if pre_emph:
        sig = pre_emphasis(sig=sig, pre_emph_coeff=0.97)

    # -> framing
    frames, frame_length = framing(sig=sig,
                                   fs=fs,
                                   win_len=win_len,
                                   win_hop=win_hop)

    # -> windowing
    windows = windowing(frames=frames,
                        frame_len=frame_length,
                        win_type=win_type)

    # -> FFT -> |.|
    fourrier_transform = np.fft.rfft(windows, nfft)
    abs_fft_values = np.abs(fourrier_transform)

    #  -> x linear-fbanks
    linear_fbanks_mat = linear_filter_banks(nfilts=nfilts,
                                            nfft=nfft,
                                            fs=fs,
                                            low_freq=low_freq,
                                            high_freq=high_freq)
    features = np.dot(abs_fft_values, linear_fbanks_mat.T)

    # -> log(.)
    # handle zeros: if feat is zero, we get problems with log
    features_no_zero = zero_handling(features)
    log_features = np.log(features_no_zero)

    #  -> DCT(.)
    lfccs = dct(x=log_features, type=dct_type, axis=1,
                norm='ortho')[:, :num_ceps]

    # liftering
    if lifter > 0:
        lfccs = lifter_ceps(lfccs, lifter)

    # normalization
    if normalize:
        lfccs = cmvn(cms(lfccs))
    return lfccs
