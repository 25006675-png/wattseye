Section
Clean Message
Data source
Models are trained on UK-DALE, which provides synchronized whole-house aggregate power and individual appliance sub-meter readings. Each appliance is learned independently: the network recovers that appliance’s consumption from the aggregate signal alone. UK-DALE houses are converted into per-channel .dat files, with aggregate power as channel 1 and the target appliance as channel 2.
Preprocessing
Aggregate and appliance signals are resampled to a common 6-second grid and forward-filled. Invalid values are removed, readings below 5 W are zeroed, and each channel is clipped using appliance-specific cutoffs to suppress outliers. The aggregate signal is then mean-normalised using training-set μ/σ, which are reused unchanged during testing.
ON/OFF labels
Ground-truth ON/OFF status is generated from appliance power using thresholds plus minimum on/off durations. Short spikes are removed and brief gaps are bridged, producing clean activation labels for F1 scoring.
Train / validation / test split
The setup follows a strict unseen-house protocol. Training uses all UK-DALE houses except House 2. Within the training pool, the first 10% is held out for validation, while the rest is used for training with sliding windows. House 2 is never seen during training and is used only for final testing. For appliances available in only one house, an 80/20 chronological split is used instead.
Model
The model is ELECTRIcity, a Transformer-based NILM model with a convolutional tokeniser, downsampling, positional embedding, transformer blocks, and deconvolutional upsampling.
Training routine
Training has two stages: unsupervised ELECTRA-style pre-training, followed by supervised fine-tuning for disaggregation. Fine-tuning uses a composite loss combining power accuracy, ON/OFF status accuracy, and appliance-specific ON-region penalties.
Validation & checkpointing
After every fine-tuning epoch, the model is evaluated on the validation split. The checkpoint that maximises F1 + accuracy − MRE is saved as the best model, then evaluated once on the held-out test house.
Scoring
On the test house, predicted power is clipped and converted into ON/OFF status using the same threshold logic. Performance is reported using F1, accuracy, precision, recall, MAE, and MRE.


Appliance
F1 Score
Kettle
0.960
Fridge
0.858
Washing machine
0.802
Hair dryer
0.762
Iron
0.675


