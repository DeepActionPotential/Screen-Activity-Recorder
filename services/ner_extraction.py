
import torch
import torch.nn as nn
from torchcrf import CRF


from schemas.ner_schemas import NEREntites, NEREntity


class BiLSTMCRF(nn.Module):
    def __init__(self, vocab_size, embedding_dim, hidden_dim, num_labels, pad_idx=0, pad_label_id=-100):
        super().__init__()
        self.pad_label_id = pad_label_id
        
        # Embedding layer for tokens
        self.embedding = nn.Embedding(vocab_size, embedding_dim, padding_idx=pad_idx)
        
        # BiLSTM layer
        self.lstm = nn.LSTM(
            input_size=embedding_dim,
            hidden_size=hidden_dim,
            num_layers=1,
            bidirectional=True,
            batch_first=True
        )
        
        # Linear layer for projecting to label space
        self.hidden2tag = nn.Linear(hidden_dim * 2, num_labels)
        
        # CRF layer
        self.crf = CRF(num_labels, batch_first=True)


    def forward(self, input_ids, tags=None, mask=None):
        embeds = self.embedding(input_ids)            # [B, L, E]
        lstm_out, _ = self.lstm(embeds)               # [B, L, 2*H]
        emissions = self.hidden2tag(lstm_out)         # [B, L, num_labels]
        
        if tags is not None:
            # Convert ignored labels to 0 for CRF
            crf_tags = tags.clone()
            crf_tags[crf_tags == self.pad_label_id] = 0
            
            # Negative log likelihood
            loss = -self.crf(emissions, crf_tags, mask=mask, reduction='mean')
            return loss
        else:
            # Decode (Viterbi) paths
            return self.crf.decode(emissions, mask=mask)
        


import torch
import torch.nn.functional as F

class NERBILSTMCRFExtractor:
    """
    Named Entity Recognition extractor using BiLSTM + CRF.
    - Handles tokenization, model inference, and decoding.
    - Follows SOLID principles: cohesive, extendable, and testable.
    """

    def __init__(self, ner_model, tokenizer, label2id, max_len=512, device='cpu'):
        self.ner_model = ner_model.to(device)
        self.tokenizer = tokenizer
        self.label2id = label2id
        self.id2label = {v: k for k, v in label2id.items()}
        self.max_len = max_len
        self.device = device

    def _prepare_inputs(self, text):
        """Tokenize and prepare inputs for the model."""
        encoding = self.tokenizer(
            text,
            truncation=True,
            padding="max_length",
            max_length=self.max_len,
            return_tensors="pt"
        )
        return encoding["input_ids"].to(self.device), encoding["attention_mask"].bool().to(self.device)

    def _decode_with_confidence(self, emissions, mask, pred_ids):
        """Decode predictions and compute confidence scores."""
        seq_len = mask[0].sum().item()
        pred_ids = pred_ids[:seq_len]

        tokens = self.tokenizer.convert_ids_to_tokens(emissions.new_tensor(range(emissions.size(1))).tolist())
        tokens = self.tokenizer.convert_ids_to_tokens(emissions.argmax(-1)[0][:seq_len].tolist())

        labels, confidences = [], []

        for i, lbl_id in enumerate(pred_ids):
            label = self.id2label.get(lbl_id, "O")
            labels.append(label)

            # confidence = softmax(emissions[timestep])[predicted_label]
            emission_scores = emissions[0, i]
            probs = F.softmax(emission_scores, dim=-1)
            confidences.append(probs[lbl_id].item())

        return labels, confidences

    def extract(self, text:str, confidence_score_threshold:float=0.5) -> NEREntites:
        """Run NER extraction and return tokens, labels, and confidence scores."""
        X, mask = self._prepare_inputs(text)

        self.ner_model.eval()
        with torch.no_grad():
            emissions = self.ner_model.embedding(X)       # embedding
            lstm_out, _ = self.ner_model.lstm(emissions)  # BiLSTM
            emissions = self.ner_model.hidden2tag(lstm_out)
            pred_ids = self.ner_model.crf.decode(emissions, mask=mask)[0]

        labels, confidences = self._decode_with_confidence(emissions, mask, pred_ids)
        tokens = self.tokenizer.convert_ids_to_tokens(X[0][:mask[0].sum()])

        return NEREntites(entities=[NEREntity(entity_text=t, entity_label=l, confidence_score=c) for t, l, c in zip(tokens, labels, confidences) if c >= confidence_score_threshold])

    def pretty_print(self, results: NEREntites):
        """Nicely print extracted tokens with labels and confidence from NEREntites."""
        print("\n=== NER Inference Output ===")
        print("| Token          | Label          | Confidence |")
        print("|----------------|----------------|------------|")
        for entity in results.entities:
            print(f"| {entity.entity:<14} | {entity.entity_label:<14} | {entity.confidence_score:.4f} |")
