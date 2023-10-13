# -*- coding: utf-8 -*-
"""Pentagram_Music_Transformer_Maker_X.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/github/asigalov61/Pentagram-Music-Transformer/blob/main/Training-Code/Pentagram_Music_Transformer_Maker_X.ipynb

# Pentagram Music Transformer Maker: X Transformer Edition (ver. 1.0)

***

Powered by tegridy-tools: https://github.com/asigalov61/tegridy-tools

***

WARNING: This complete implementation is a functioning model of the Artificial Intelligence. Please excercise great humility, care, and respect. https://www.nscai.gov/

***

#### Project Los Angeles

#### Tegridy Code 2023

***

# GPU check
"""

!nvidia-smi

"""# Setup environment"""

!git clone https://github.com/asigalov61/tegridy-tools

!pip install --upgrade pip
!pip3 install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu121
!pip install torch-summary
!pip install tqdm
!pip install matplotlib

# Commented out IPython magic to ensure Python compatibility.
# Load modules and make data dir

print('Loading modules...')

import os
import pickle
import random
import secrets
import tqdm
import math
import torch
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset

import matplotlib.pyplot as plt

from torchsummary import summary
from sklearn import metrics

# %cd /content/tegridy-tools/tegridy-tools/

import TMIDIX

# %cd /content/tegridy-tools/tegridy-tools/X-Transformer

from x_transformer_1_23_2 import *

torch.set_float32_matmul_precision('high')
torch.backends.cuda.matmul.allow_tf32 = True # allow tf32 on matmul
torch.backends.cudnn.allow_tf32 = True # allow tf32 on cudnn

# %cd /content/

if not os.path.exists('/content/INTS'):
    os.makedirs('/content/INTS')

import random

print('Done')

"""# Load training data"""

dataset_addr = "/content/INTS"

SEQ_LEN = 8192 # Models seq len
PAD_IDX = 1670 # Models pad index

CHUNKS_LENGTH = int(math.ceil(SEQ_LEN / 10) * 10) # chunks length that is larger than swq_len and divisible by 5 and 2
MIN_NUMBER_OF_CHUNK_EVENTS = 520 # min number of tokens per chunk

#==========================================================================

filez = list()
for (dirpath, dirnames, filenames) in os.walk(dataset_addr):
    filez += [os.path.join(dirpath, file) for file in filenames]
print('=' * 70)

filez.sort()

#==========================================================================

print('Loading training data... Please wait...')
print('=' * 70)

train_data = []

chunks_counter = 0
discarted_chunks_counter = 0

for f in tqdm.tqdm(filez):
  train_d = pickle.load(open(f, 'rb'))
  random.shuffle(train_d)
  for t in train_d:
    for i in range(0, len(t), CHUNKS_LENGTH):

      #=========================================================================
      # collecting all possible chunks of chunks length

      if 0 <= max(t[i:i+CHUNKS_LENGTH]) < PAD_IDX: # final data integrity check
        if len(t[i:i+CHUNKS_LENGTH]) == CHUNKS_LENGTH:
          train_data.append(t[i:i+CHUNKS_LENGTH])

        else:
          if len(t[i:i+CHUNKS_LENGTH]) > MIN_NUMBER_OF_CHUNK_EVENTS:
            td = t[i:i+CHUNKS_LENGTH] + [PAD_IDX] * (CHUNKS_LENGTH-len(t[i:i+CHUNKS_LENGTH])) # padding with pad index
            train_data.append(td)
          else:
            discarted_chunks_counter += 1

        chunks_counter += 1

    #=========================================================================
    # Collecting middle chunk if it larger than chunks length

    if 0 <= max(t) < PAD_IDX: # final data integrity check
        if len(t) > CHUNKS_LENGTH+10:
            sidx = (int((len(t) // 2) / 5) * 5)-(CHUNKS_LENGTH // 2)
            train_data.append(t[sidx:sidx+CHUNKS_LENGTH])

        else:
            discarted_chunks_counter += 1

        chunks_counter += 1
#==========================================================================

print('=' * 70)
print('Total number of imput chunks:', chunks_counter)
print('Total number of good chunks:', len(train_data))
print('Total number of discarted chunks:', discarted_chunks_counter, '/', round(100 * discarted_chunks_counter/chunks_counter, 3), '%')
print('All data is good:', len(max(train_data, key=len)) == len(min(train_data, key=len)))
print('=' * 70)
print('Final data randomization...')
random.shuffle(train_data)
print('Done!')
print('=' * 70)

len(train_data)

train_data[0][:10], train_data[0][-10:]

len(train_data) // 16

"""# Setup model"""

# Setup model

# constants

BATCH_SIZE = 1
NUM_EPOCHS = 1
GRADIENT_ACCUMULATE_EVERY = 16

NUM_BATCHES = (len(train_data) // BATCH_SIZE // GRADIENT_ACCUMULATE_EVERY) * NUM_EPOCHS

LEARNING_RATE = 2e-4

VALIDATE_EVERY  = 100
SAVE_EVERY = 500
GENERATE_EVERY  = 100
PRINT_STATS_EVERY = 20

GENERATE_LENGTH = 32

# helpers

def cycle(loader):
    while True:
        for data in loader:
            yield data

# instantiate the model

model = TransformerWrapper(
    num_tokens = PAD_IDX+1,
    max_seq_len = SEQ_LEN,
    attn_layers = Decoder(dim = 1024, depth = 40, heads = 32, attn_flash = True)
    )

model = AutoregressiveWrapper(model, ignore_index = PAD_IDX)

model.cuda()

print('Done!')

summary(model)

# Dataloader

class MusicDataset(Dataset):
    def __init__(self, data, seq_len):
        super().__init__()
        self.data = data
        self.seq_len = seq_len

    def __getitem__(self, index):

        # consequtive sampling

        full_seq = torch.Tensor(self.data[index][:self.seq_len+1]).long()

        return full_seq.cuda()

    def __len__(self):
        return (len(self.data) // BATCH_SIZE) * BATCH_SIZE

train_dataset = MusicDataset(train_data, SEQ_LEN)
val_dataset   = MusicDataset(train_data, SEQ_LEN)
train_loader  = cycle(DataLoader(train_dataset, batch_size = BATCH_SIZE))
val_loader    = cycle(DataLoader(val_dataset, batch_size = BATCH_SIZE))

# precision/optimizer/scaler

dtype = torch.float16

ctx = torch.amp.autocast(device_type='cuda', dtype=dtype)

optim = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)

scaler = torch.cuda.amp.GradScaler(enabled=(dtype == dtype))

"""# Train"""

# Train the model

train_losses = []
val_losses = []

train_accs = []
val_accs = []

for i in tqdm.tqdm(range(NUM_BATCHES), mininterval=10., desc='Training'):
    model.train()

    for __ in range(GRADIENT_ACCUMULATE_EVERY):
        with ctx:
            loss, acc = model(next(train_loader))
            loss = loss / GRADIENT_ACCUMULATE_EVERY
            scaler.scale(loss).backward()

    if i % PRINT_STATS_EVERY == 0:
        print(f'Training loss: {loss.item() * GRADIENT_ACCUMULATE_EVERY}')
        print(f'Training acc: {acc.item()}')

    train_losses.append(loss.item() * GRADIENT_ACCUMULATE_EVERY)
    train_accs.append(acc.item())

    scaler.unscale_(optim)
    torch.nn.utils.clip_grad_norm_(model.parameters(), 0.5)
    scaler.step(optim)
    scaler.update()
    optim.zero_grad(set_to_none=True)

    if i % VALIDATE_EVERY == 0:
        model.eval()
        with torch.no_grad():
            with ctx:
                val_loss, val_acc = model(next(val_loader))

                print(f'Validation loss: {val_loss.item()}')
                print(f'Validation acc: {val_acc.item()}')

                val_losses.append(val_loss.item())
                val_accs.append(val_acc.item())

                print('Plotting training loss graph...')

                tr_loss_list = train_losses
                plt.plot([i for i in range(len(tr_loss_list))] ,tr_loss_list, 'b')
                plt.show()
                plt.close()
                print('Done!')

                print('Plotting training acc graph...')

                tr_loss_list = train_accs
                plt.plot([i for i in range(len(tr_loss_list))] ,tr_loss_list, 'b')
                plt.show()
                plt.close()
                print('Done!')

                print('Plotting validation loss graph...')
                tr_loss_list = val_losses
                plt.plot([i for i in range(len(tr_loss_list))] ,tr_loss_list, 'b')
                plt.show()
                plt.close()
                print('Done!')

                print('Plotting validation acc graph...')
                tr_loss_list = val_accs
                plt.plot([i for i in range(len(tr_loss_list))] ,tr_loss_list, 'b')
                plt.show()
                plt.close()
                print('Done!')

    if i % GENERATE_EVERY == 0:
        model.eval()

        inp = random.choice(val_dataset)[:-1]

        print(inp)

        with ctx:
            sample = model.generate(inp[None, ...], GENERATE_LENGTH)

        print(sample)

    if i % SAVE_EVERY == 0:

        print('Saving model progress. Please wait...')
        print('model_checkpoint_' + str(i) + '_steps_' + str(round(float(train_losses[-1]), 4)) + '_loss_' + str(round(float(train_accs[-1]), 4)) + '_acc.pth')

        fname = '/content/model_checkpoint_' + str(i) + '_steps_' + str(round(float(train_losses[-1]), 4)) + '_loss_' + str(round(float(train_accs[-1]), 4)) + '_acc.pth'

        torch.save(model.state_dict(), fname)

        data = [train_losses, train_accs, val_losses, val_accs]

        TMIDIX.Tegridy_Any_Pickle_File_Writer(data, '/content/losses_accs')

        print('Done!')

"""# Final Save"""

print('Saving model progress. Please wait...')
print('model_checkpoint_' + str(i) + '_steps_' + str(round(float(train_losses[-1]), 4)) + '_loss_' + str(round(float(train_accs[-1]), 4)) + '_acc.pth')

fname = '/content/model_checkpoint_' + str(i) + '_steps_' + str(round(float(train_losses[-1]), 4)) + '_loss_' + str(round(float(train_accs[-1]), 4)) + '_acc.pth'

torch.save(model.state_dict(), fname)

print('Done!')

data = [train_losses, train_accs, val_losses, val_accs]

TMIDIX.Tegridy_Any_Pickle_File_Writer(data, '/content/losses_accuracies')

# Save training loss graph

plt.plot([i for i in range(len(train_losses))] ,train_losses, 'b')
plt.savefig('/content/training_loss_graph.png')
plt.close()
print('Done!')

# Save training acc graph

plt.plot([i for i in range(len(train_accs))] ,train_accs, 'b')
plt.savefig('/content/training_acc_graph.png')
plt.close()
print('Done!')

# Save validation loss graph

plt.plot([i for i in range(len(val_losses))] ,val_losses, 'b')
plt.savefig('/content/validation_loss_graph.png')
plt.close()
print('Done!')

# Save validation acc graph

plt.plot([i for i in range(len(val_accs))] ,val_accs, 'b')
plt.savefig('/content/validation_acc_graph.png')
plt.close()
print('Done!')

"""# Eval"""

f = '/content/Pentagram-Music-Transformer-MI-Seed-1.mid'

print('=' * 70)
print('Pentagram Music Transformer Seed MIDI Loader')
print('=' * 70)
print('Loading seed MIDI...')
print('=' * 70)
print('File:', f)
print('=' * 70)

#=======================================================
# START PROCESSING

# Convering MIDI to ms score with MIDI.py module
score = TMIDIX.midi2single_track_ms_score(open(f, 'rb').read(), recalculate_channels=False)

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
      events_matrix1.sort(key=lambda x: x[3])
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

      chords_counter = 1

      comp_chords_len = len([y for y in melody_chords if y[0] != 0])

      for m in melody_chords:

          if chords_counter % 50 == 0:
              nct = 1025+min(511, ((chords_counter // 50)-1)) # chords counter token
              melody_chords2.extend([nct, nct, nct, nct, nct])

          if m[2] != 9:
              ptc = m[3]
              pat = m[5]
          else:
              ptc = m[3] + 128
              pat = 128

          melody_chords2.extend([pat, m[0]+129, m[1]+385, ptc+641, m[4]+897])

          if m[0] != 0:
              chords_counter += 1

#=======================================================

torch.backends.cuda.matmul.allow_tf32 = True # allow tf32 on matmul
torch.backends.cudnn.allow_tf32 = True # allow tf32 on cudnn

device_type = 'cuda'
dtype = 'float16'

ptdtype = {'float32': torch.float32, 'bfloat16': torch.bfloat16, 'float16': torch.float16}[dtype]

ctx = torch.amp.autocast(device_type=device_type, dtype=ptdtype)

model.eval()

#x = (torch.tensor(random.choice(train_data)[:1000], dtype=torch.long, device=device_type)[None, ...])
#x = torch.tensor([[1669, 1669, 1669, 1538+1, 1540+40]], dtype=torch.long, device=device_type)
x = torch.tensor([[1669, 1669, 1669]], dtype=torch.long, device=device_type)

#x = torch.tensor([melody_chords2[:1000]], dtype=torch.long, device=device_type)


# run generation

with ctx:
  out = model.generate(x,
                        500,
                        temperature=0.9,
                        return_prime=True,
                        verbose=True)

y = out.tolist()

print('---------------')

#@title Test INTs

data = y[0].tolist()

print('Sample INTs', data[:15])

out = data[:200000]

if len(out) != 0:

    song = out
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
                                                    output_file_name = '/content/Pentagram-Music-Transformer-Composition',
                                                    track_name='Project Los Angeles',
                                                    list_of_MIDI_patches=patches
                                                    )

print('Done!')

patches

tok_emb = model.transformer.wte.weight.detach().cpu().tolist()

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
plt.savefig("/content/Pentagram-Music-Transformer-Tokens-Embeddings-Plot.png", bbox_inches="tight")

"""# Congrats! You did it! :)"""