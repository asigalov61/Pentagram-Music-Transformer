# -*- coding: utf-8 -*-
"""Pentagram_Music_Transformer_X.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1q-xMMJ3diMgdBxFTHwiz1t0xKSU1ZAt1

# Pentagram Music Transformer (ver. 1.0)

***

Powered by tegridy-tools: https://github.com/asigalov61/tegridy-tools

***

WARNING: This complete implementation is a functioning model of the Artificial Intelligence. Please excercise great humility, care, and respect. https://www.nscai.gov/

***

#### Project Los Angeles

#### Tegridy Code 2023

***

# (NVIDIA GPU CHECK)
"""

# @title NVIDIA GPU check
!nvidia-smi

"""# (SETUP ENVIRONMENT)"""

#@title Install dependencies
!git clone --depth 1 https://github.com/asigalov61/Pentagram-Music-Transformer
!pip install huggingface_hub
!pip install torch
!pip install einops
!pip install torch-summary
!pip install tqdm
!pip install matplotlib
!apt install fluidsynth #Pip does not work for some reason. Only apt works
!pip install midi2audio

# Commented out IPython magic to ensure Python compatibility.
# @title Import modules

print('=' * 70)
print('Loading Pentagram Music Transformer modules...')
print('Please wait...')
print('=' * 70)

import os
import tqdm

import torch

# %cd /content/Pentagram-Music-Transformer

from x_transformer_1_23_2 import *

import TMIDIX

# %cd /content/

from torchsummary import summary

from sklearn import metrics

import matplotlib.pyplot as plt

from midi2audio import FluidSynth
from IPython.display import Audio, display

from huggingface_hub import hf_hub_download

from google.colab import files

print('=' * 70)
print('Done!')
print('Enjoy! :)')
print('=' * 70)

"""# (LOAD MODEL)"""

#@title Load Pentagram Music Transformer Small Pre-Trained Model

#@markdown Very fast model (fp16), 32 heads, 40 layers, 245k MIDIs training corpus

full_path_to_model_checkpoint = "/content/Pentagram-Music-Transformer/Models/Large/Pentagram_Music_Transformer_Large_Test_Trained_Model_19251_steps_0.6022_loss_0.8257_acc.pth" #@param {type:"string"}

plot_tokens_embeddings = True # @param {type:"boolean"}

print('=' * 70)
print('Loading Pentagram Music Transformer Small Pre-Trained Model...')
print('Please wait...')
print('=' * 70)

if os.path.isfile(full_path_to_model_checkpoint):
  print('Model already exists...')

else:
  hf_hub_download(repo_id='asigalov61/Pentagram-Music-Transformer',
                  filename='Pentagram_Music_Transformer_Large_Test_Trained_Model_19251_steps_0.6022_loss_0.8257_acc.pth',
                  local_dir='/content/Pentagram-Music-Transformer/Models/Large',
                  local_dir_use_symlinks=False)
print('=' * 70)
print('Instantiating model...')

torch.backends.cuda.matmul.allow_tf32 = True # allow tf32 on matmul
torch.backends.cudnn.allow_tf32 = True # allow tf32 on cudnn
device_type = 'cuda'
dtype = 'bfloat16' if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else 'float16' # 'float32', 'bfloat16', or 'float16', the latter will auto implement a GradScaler
ptdtype = {'float32': torch.float32, 'bfloat16': torch.bfloat16, 'float16': torch.float16}[dtype]
ctx = torch.amp.autocast(device_type=device_type, dtype=ptdtype)

# instantiate the model

SEQ_LEN = 8192 # Models seq len
PAD_IDX = 1670 # Models pad index

model = TransformerWrapper(
    num_tokens = PAD_IDX+1,
    max_seq_len = SEQ_LEN,
    attn_layers = Decoder(dim = 1024, depth = 40, heads = 32, attn_flash = True)
    )

model = AutoregressiveWrapper(model, ignore_index = PAD_IDX)

model.cuda()

print('=' * 70)
print('Loading model checkpoint...')

model.load_state_dict(torch.load(full_path_to_model_checkpoint))

print('=' * 70)

model.eval()

print('Done!')
print('=' * 70)
print('Model will use', dtype, 'precision')
print('=' * 70)

# Model stats
print('Model summary:')
summary(model)

# Plot Token Embeddings
if plot_tokens_embeddings:
  tok_emb = model.net.token_emb.emb.weight.detach().cpu().tolist()

  cos_sim = metrics.pairwise_distances(
    tok_emb, metric='cosine'
  )
  plt.figure(figsize=(7, 7))
  plt.imshow(cos_sim, cmap="inferno", interpolation="nearest")
  im_ratio = cos_sim.shape[0] / cos_sim.shape[1]
  plt.colorbar(fraction=0.046 * im_ratio, pad=0.04)
  plt.xlabel("Position")
  plt.ylabel("Position")
  plt.tight_layout()
  plt.plot()
  plt.savefig("/content/Pentagram-Music-Transformer-Large-Tokens-Embeddings-Plot.png", bbox_inches="tight")

"""# (GENERATE)

# (IMPROV)
"""

# @title Standard Improv Generator

#@markdown Custom improv settings allow you to specify some improv parameters. If this option is not selected, the model will choose improv settings itself

use_custom_improv_settings = False # @param {type:"boolean"}

#@markdown Custom improv settings

lead_instrument_MIDI_patch_number = 0 # @param {type:"slider", min:0, max:128, step:1}
add_drums = False # @param {type:"boolean"}

#@markdown Generation Settings

number_of_tokens_to_generate = 500 # @param {type:"slider", min:15, max:4095, step:5}
number_of_batches_to_generate = 4 # @param {type:"slider", min:1, max:16, step:1}
temperature = 0.9 # @param {type:"slider", min:0.1, max:1, step:0.1}

#@markdown Other settings

render_MIDI_to_audio = True # @param {type:"boolean"}

print('=' * 70)
print('Pentagram Music Transformer Improv Model Generator')
print('=' * 70)

if add_drums:
  drumsp = 1
else:
  drumsp = 0

if use_custom_improv_settings:
  inp = torch.tensor([[1669, 1669, 1669, 1538+drumsp, 1540+lead_instrument_MIDI_patch_number]] * number_of_batches_to_generate,
                     dtype=torch.long,
                     device=device_type)

else:
  inp = torch.tensor([[1669, 1669, 1669]] * number_of_batches_to_generate,
                    dtype=torch.long,
                    device=device_type)

print('Selected improv sequence:')
print(inp[0].tolist())
print('=' * 70)

# run generation
with ctx:
  out = model.generate(inp,
                      number_of_tokens_to_generate,
                      temperature=temperature,
                      return_prime=False)

outy = out.tolist()

print('=' * 70)
print('Done!')
print('=' * 70)

#======================================================================

print('Rendering results...')

for i in range(number_of_batches_to_generate):

  print('=' * 70)
  print('Batch #', i)
  print('=' * 70)

  out1 = outy[i]

  print('Sample INTs', out1[:10])
  print('=' * 70)

  if len(out1) != 0:

      song = out1
      song_f = []
      time = 0
      dur = 0
      vel = 90
      pitch = 0
      channel = 0

      patches = [0] * 16

      channels = [0] * 16
      channels[9] = 1


      for ss in song:

        if ss >= 0 and ss <= 128:

          if ss < 128:

              if ss not in patches:
                cha = channels.index(0)
                channels[cha] = 1

                patches[cha] = ss
                channel = patches.index(ss)
              else:
                channel = patches.index(ss)

          if ss == 128:
              channel = 9

        if ss > 128 and ss <= 256:

          time += (ss-129) * 8

        if ss > 384 and ss <= 640:

          dur = (ss-385) * 16

        if ss > 640 and ss <= 896:

          pitch = (ss-641) % 128

        if ss > 896 and ss <= 1024:

          vel = (ss-897)

          song_f.append(['note', time, dur, channel, pitch, vel ])

      detailed_stats = TMIDIX.Tegridy_ms_SONG_to_MIDI_Converter(song_f,
                                                                output_signature = 'Pentagram Music Transformer',
                                                                output_file_name = '/content/Pentagram-Music-Transformer-Composition_'+str(i),
                                                                track_name='Project Los Angeles',
                                                                list_of_MIDI_patches=patches
                                                                )
      print('Done!')


  print('=' * 70)
  print('Displaying resulting composition...')
  print('=' * 70)

  fname = '/content/Pentagram-Music-Transformer-Composition_'+str(i)

  x = []
  y =[]
  c = []

  colors = ['red', 'yellow', 'green', 'cyan', 'blue', 'pink', 'orange', 'purple', 'gray', 'white', 'gold', 'silver', 'red', 'yellow', 'green', 'cyan']

  for s in song_f:
    x.append(s[1] / 1000)
    y.append(s[4])
    c.append(colors[s[3]])

  if render_MIDI_to_audio:
    FluidSynth("/usr/share/sounds/sf2/FluidR3_GM.sf2", 16000).midi_to_audio(str(fname + '.mid'), str(fname + '.wav'))
    display(Audio(str(fname + '.wav'), rate=16000))

  plt.figure(figsize=(14,5))
  ax=plt.axes(title=fname)
  ax.set_facecolor('black')

  plt.scatter(x,y, c=c)
  plt.xlabel("Time")
  plt.ylabel("Pitch")
  plt.show()

"""# (CUSTOM MIDI)"""

# @title Upload your own custom MIDI

#@markdown Press the play button to summon MIDI file upload widget

render_MIDI_to_audio = False # @param {type:"boolean"}

print('=' * 70)
print('Pentagram Music Transformer Seed MIDI Loader')
print('=' * 70)

uploaded_MIDI = files.upload()

if list(uploaded_MIDI.keys()):
  print('=' * 70)
  score = TMIDIX.midi2single_track_ms_score(list(uploaded_MIDI.values())[0], recalculate_channels=False)
  f = list(uploaded_MIDI.keys())[0]
  print('Loading seed MIDI...')
  print('=' * 70)
  print('File:', f)

  #=======================================================
  # START PROCESSING

  # INSTRUMENTS CONVERSION CYCLE
  events_matrix = []
  itrack = 1
  patches = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

  while itrack < len(score):
      for event in score[itrack]:
          if event[0] == 'note' or event[0] == 'patch_change':
              events_matrix.append(event)
      itrack += 1

  events_matrix.sort(key=lambda x: x[1])

  events_matrix1 = []

  for event in events_matrix:
          if event[0] == 'patch_change':
                patches[event[2]] = event[3]

          if event[0] == 'note':
                event.extend([patches[event[3]]])

                events_matrix1.append(event)

  if len(events_matrix1) > 0:
    if min([e[1] for e in events_matrix1]) >= 0 and min([e[2] for e in events_matrix1]) >= 0:

      #=======================================================
      # PRE-PROCESSING

      # checking number of instruments in a composition
      instruments_list_without_drums = list(set([y[3] for y in events_matrix1 if y[3] != 9]))
      instruments_list = list(set([y[3] for y in events_matrix1]))

      if len(events_matrix1) > 0 and len(instruments_list_without_drums) > 0:

        # recalculating timings
        for e in events_matrix1:
            e[1] = int(e[1] / 8) # Max 2 seconds for start-times
            e[2] = int(e[2] / 16) # Max 4 seconds for durations

        # Sorting by pitch, then by start-time
        events_matrix1.sort(key=lambda x: x[4], reverse=True)
        events_matrix1.sort(key=lambda x: x[1])

        #=======================================================
        # FINAL PRE-PROCESSING

        melody_chords = []

        pe = events_matrix1[0]

        for e in events_matrix1:

            # Cliping all values...
            time = max(0, min(255, e[1]-pe[1]))
            dur = max(0, min(255, e[2]))
            cha = max(0, min(15, e[3]))
            ptc = max(1, min(127, e[4]))

            # Calculating octo-velocity
            vel = max(1, min(127, e[5]))

            pat = max(0, min(127, e[6]))

            # Writing final note
            melody_chords.append([time, dur, cha, ptc, vel, pat])

            pe = e



        #=======================================================
        # FINAL PROCESSING
        #=======================================================

        melody_chords2 = []

        # Break between compositions / Intro seq

        if 9 in instruments_list:
          drums_present = 1539 # Yes
        else:
          drums_present = 1538 # No

        if melody_chords[0][2] != 9:
            pat = melody_chords[0][5]
        else:
            pat = 128

        melody_chords2.extend([1669, 1669, 1669, drums_present, 1540+pat])

        #=======================================================

        # TOTAL DICTIONARY SIZE 1669+1=1670

        #=======================================================
        # MAIN PROCESSING CYCLE
        #=======================================================

        note_counter = 1

        for m in melody_chords:

            if note_counter % 100 == 0:
                nct = 1025+min(511, (note_counter // 100)) # note counter token
                melody_chords2.extend([nct, nct, nct, nct, nct])

            if m[2] != 9:
                ptc = m[3]
                pat = m[5]
            else:
                ptc = m[3] + 128
                pat = 128

            melody_chords2.extend([pat, m[0]+129, m[1]+385, ptc+641, m[4]+897])

            note_counter += 1

#=======================================================

print('=' * 70)
print('Composition stats:')
print('Composition has', len(melody_chords2) // 5, 'notes')
print('Composition has', len(melody_chords2), 'tokens')
print('=' * 70)

data = melody_chords2

print('Sample INTs:', data[:10])
print('=' * 70)

if len(data) != 0:

    song = data
    song_f = []
    time = 0
    dur = 0
    vel = 90
    pitch = 0
    channel = 0

    patches = [0] * 16

    channels = [0] * 16
    channels[9] = 1


    for ss in song:

      if ss >= 0 and ss <= 128:

        if ss < 128:

            if ss not in patches:
              cha = channels.index(0)
              channels[cha] = 1

              patches[cha] = ss
              channel = patches.index(ss)
            else:
              channel = patches.index(ss)

        if ss == 128:
            channel = 9

      if ss > 128 and ss <= 256:

        time += (ss-129) * 8

      if ss > 384 and ss <= 640:

        dur = (ss-385) * 16

      if ss > 640 and ss <= 896:

        pitch = (ss-641) % 128

      if ss > 896 and ss <= 1024:

        vel = (ss-897)

        song_f.append(['note', time, dur, channel, pitch, vel ])

    detailed_stats = TMIDIX.Tegridy_ms_SONG_to_MIDI_Converter(song_f,
                                                              output_signature = 'Pentagram Music Transformer',
                                                              output_file_name = '/content/Pentagram-Music-Transformer-Seed-Composition',
                                                              track_name='Project Los Angeles',
                                                              list_of_MIDI_patches=patches
                                                              )
    print('Done!')


print('=' * 70)
print('Displaying resulting composition...')
print('=' * 70)

fname = '/content/Pentagram-Music-Transformer-Seed-Composition'

x = []
y =[]
c = []

colors = ['red', 'yellow', 'green', 'cyan', 'blue', 'pink', 'orange', 'purple', 'gray', 'white', 'gold', 'silver', 'red', 'yellow', 'green', 'cyan']

for s in song_f:
  x.append(s[1] / 1000)
  y.append(s[4])
  c.append(colors[s[3]])

if render_MIDI_to_audio:
  FluidSynth("/usr/share/sounds/sf2/FluidR3_GM.sf2", 16000).midi_to_audio(str(fname + '.mid'), str(fname + '.wav'))
  display(Audio(str(fname + '.wav'), rate=16000))

plt.figure(figsize=(14,5))
ax=plt.axes(title=fname)
ax.set_facecolor('black')

plt.scatter(x,y, c=c)
plt.xlabel("Time")
plt.ylabel("Pitch")
plt.show()

"""# (CONTINUATION)"""

# @title Standard Continuation Generator

#@markdown Generation Settings
try_to_generate_outro = False # @param {type:"boolean"}
number_of_prime_tokens = 6955 # @param {type:"slider", min:15, max:8192, step:5}
number_of_tokens_to_generate = 1030 # @param {type:"slider", min:15, max:4095, step:5}
number_of_batches_to_generate = 4 # @param {type:"slider", min:1, max:16, step:1}
temperature = 0.9 # @param {type:"slider", min:0.1, max:1, step:0.1}

#@markdown Other settings

include_prime_tokens_in_returned_output = False # @param {type:"boolean"}
allow_model_to_stop_generation_if_needed = False # @param {type:"boolean"}
render_MIDI_to_audio = True # @param {type:"boolean"}

print('=' * 70)
print('Pentagram Music Transformer Standard Continuation Model Generator')
print('=' * 70)

if allow_model_to_stop_generation_if_needed:
  mst = 1669

else:
  mst = None

comp = melody_chords2[:number_of_prime_tokens]

if try_to_generate_outro:
  comp.extend([1537, 1537, 1537, 1537, 1537])

inp = torch.tensor([comp] * number_of_batches_to_generate,
                    dtype=torch.long,
                    device=device_type)

print('Selected improv sequence:')
print(inp[0].tolist()[:10])
print('=' * 70)

# run generation
with ctx:
  out = model.generate(inp,
                      number_of_tokens_to_generate,
                      temperature=temperature,
                      eos_token=mst,
                      return_prime=include_prime_tokens_in_returned_output)

outy = out.tolist()

print('=' * 70)
print('Done!')
print('=' * 70)

#======================================================================

print('Rendering results...')

for i in range(number_of_batches_to_generate):

  print('=' * 70)
  print('Batch #', i)
  print('=' * 70)

  out1 = outy[i]

  print('Sample INTs', out1[:10])
  print('=' * 70)

  if len(out1) != 0:

      song = out1
      song_f = []
      time = 0
      dur = 0
      vel = 90
      pitch = 0
      channel = 0

      patches = [0] * 16

      channels = [0] * 16
      channels[9] = 1


      for ss in song:

        if ss >= 0 and ss <= 128:

          if ss < 128:

              if ss not in patches:
                cha = channels.index(0)
                channels[cha] = 1

                patches[cha] = ss
                channel = patches.index(ss)
              else:
                channel = patches.index(ss)

          if ss == 128:
              channel = 9

        if ss > 128 and ss <= 256:

          time += (ss-129) * 8

        if ss > 384 and ss <= 640:

          dur = (ss-385) * 16

        if ss > 640 and ss <= 896:

          pitch = (ss-641) % 128

        if ss > 896 and ss <= 1024:

          vel = (ss-897)

          song_f.append(['note', time, dur, channel, pitch, vel ])

      detailed_stats = TMIDIX.Tegridy_ms_SONG_to_MIDI_Converter(song_f,
                                                                output_signature = 'Pentagram Music Transformer',
                                                                output_file_name = '/content/Pentagram-Music-Transformer-Composition_'+str(i),
                                                                track_name='Project Los Angeles',
                                                                list_of_MIDI_patches=patches
                                                                )
      print('Done!')


  print('=' * 70)
  print('Displaying resulting composition...')
  print('=' * 70)

  fname = '/content/Pentagram-Music-Transformer-Composition_'+str(i)

  x = []
  y =[]
  c = []

  colors = ['red', 'yellow', 'green', 'cyan', 'blue', 'pink', 'orange', 'purple', 'gray', 'white', 'gold', 'silver', 'red', 'yellow', 'green', 'cyan']

  for s in song_f:
    x.append(s[1] / 1000)
    y.append(s[4])
    c.append(colors[s[3]])

  if render_MIDI_to_audio:
    FluidSynth("/usr/share/sounds/sf2/FluidR3_GM.sf2", 16000).midi_to_audio(str(fname + '.mid'), str(fname + '.wav'))
    display(Audio(str(fname + '.wav'), rate=16000))

  plt.figure(figsize=(14,5))
  ax=plt.axes(title=fname)
  ax.set_facecolor('black')

  plt.scatter(x,y, c=c)
  plt.xlabel("Time")
  plt.ylabel("Pitch")
  plt.show()

"""# Congrats! You did it! :)"""