# ML Algorithm Families Reference

> Reference data — presented to user when exploring ML/AI algorithm and model preferences. May need periodic updates.
> Last verified: 2026-04-24

---

## Algorithm Families

| Family | Examples | Best For | Complexity |
|--------|----------|----------|-----------|
| Classical ML | Linear/logistic regression, SVM, decision trees, random forest, XGBoost | Structured/tabular data, when you need interpretability | Low-Medium |
| Neural networks | MLP, feedforward networks | Non-linear patterns in structured data, moderate-size datasets | Medium |
| Deep learning — NLP | Transformers, BERT, GPT (fine-tune), RNNs, LSTMs | Text classification, NER, sentiment, sequence tasks | High |
| Deep learning — Vision | CNNs, ResNet, YOLO, Vision Transformers | Image classification, object detection, segmentation | High |
| Deep learning — Generative | GANs, VAEs, Diffusion models | Image/content generation, data augmentation | Very High |
| Reinforcement learning | Q-learning, PPO, A3C, RLHF | Game AI, robotics, optimization, LLM alignment | Very High |
| Recommendation systems | Collaborative filtering, matrix factorization, two-tower models | Product/content recommendations | Medium-High |
| Time series | ARIMA, Prophet, temporal CNNs, transformers | Forecasting, anomaly detection in time data | Medium |
| Graph neural networks | GCN, GAT, GraphSAGE | Social networks, molecules, knowledge graphs | High |
| Clustering / unsupervised | K-means, DBSCAN, autoencoders | Grouping, anomaly detection, dimensionality reduction | Low-Medium |

## Out-of-Scope Guidance

When an algorithm choice is beyond what the toolkit can implement, point the user to these resources:

### Frameworks
- **PyTorch** — most popular for research and production
- **TensorFlow** — Google ecosystem, strong deployment tools
- **JAX** — high-performance numerical computing
- **scikit-learn** — classical ML, quick prototyping
- **XGBoost / LightGBM** — gradient boosting for tabular data
- **Hugging Face Transformers** — pre-trained NLP and vision models

### Managed Platforms
- **AWS SageMaker** — end-to-end ML on AWS
- **Google Vertex AI** — end-to-end ML on GCP
- **Azure ML** — end-to-end ML on Azure
- **Weights & Biases** — experiment tracking and model management

### Learning Resources
- **fast.ai** — practical deep learning courses
- **Coursera ML Specialization** — foundational ML courses
- **Papers With Code** — latest research with implementations

### Pre-trained Model Hubs
- **Hugging Face Model Hub** — largest open model repository
- **TensorFlow Hub** — pre-trained TF models
- **PyTorch Hub** — pre-trained PyTorch models

### Communities
- **r/MachineLearning** — research discussion
- **ML Discord communities** — real-time help
- **Kaggle** — competitions, notebooks, datasets
