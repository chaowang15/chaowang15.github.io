---
layout: note
title: "生成模型 / Generative Models"
description: "Notes on generative models."
---

# 生成模型概览 / Generative Models Overview

## 1. 简介

首先介绍一下 **Generative Modeling 生成器模型**。Generative Modeling 是 unsupervised learning 的一种，它的核心目的是，给定 training data，重建出和其分布（distribution）一致的结果。这里“分布一致”通常体现为，重建结果和输入非常相似。如下图所示，生成器模型要估计的是一个数据分布 $p_{model}$，它应当和训练数据的 groundtruth 分布 $p_{data}$ 非常接近。

![Untitled](/assets/notes/deep-learning/generative-models/Untitled%204.png)

根据方法不同分为两类：

- 第一类方法：显式定义并估计数据的 distribution function，例如 Fully Visible belief network (FVBN) 和 AutoEncoders（比如 VAE）。
- 另一类方法：隐式估计，即并不直接估计这个 distribution function，而是（通过神经网络）直接从数据分布中采样来估计这个分布。例如GAN。

![Untitled](/assets/notes/deep-learning/generative-models/Untitled%205.png)

## 2. Fully Visible belief network (FVBN) 简介

> 参考：
> 
> - Stanford CS 231n 视频教程：[https://youtu.be/5WoItGTWV54?t=26m32s。这个视频从打开的位置开始就是](https://youtu.be/5WoItGTWV54?t=26m32s。这个视频从打开的位置开始就是) VAE 这一块。该视频对应的课件：[http://cs231n.stanford.edu/slides/2021/lecture_12.pdf](http://cs231n.stanford.edu/slides/2021/lecture_12.pdf)

首先简介一下 **Fully Visible belief network (FVBN)**。它定义了一个显式的、Tractable 数据概率分布（Explicit Density Model）的表达式，其重建的 target 就是为了估计这个数据分布 P(X)。FVBN 就是 Section 2.1 介绍的**有显式定义的 Generative Models 的一种常见类型**。

显然，通常情况下，一个数据（例如一张图片）的 P(X) 是由全部的 pixels 的联合概率来决定，如下：

![Untitled](/assets/notes/deep-learning/generative-models/Untitled%206.png)

一种直观的估计 P(X) 的思路是使用链式法则，即 P(X) 等于全部 pixels 的概率乘积，同时每个 pixel 的概率又取决于此前已经估计出来的所有 pixels 的条件概率。这就类似 RNN/LSTM 的思想，而 PixelRNN 算法就是基于此。

![Untitled](/assets/notes/deep-learning/generative-models/Untitled%207.png)

PixelRNN 算法从 corner 开始向内部延伸，通过一个 RNN/LSTM 网络来学习 pixels 之间的关系，从而进行预测。它一个明显的缺点就是训练和测试的速度都很慢。

![Untitled](/assets/notes/deep-learning/generative-models/Untitled%208.png)

改进版本的 PixelCNN 网络稍有不同，它使用了 CNN kernel 来估计每个 pixel。即每个 pixel 此时只依赖于一个 CNN kernel 中的其他 pixels 了。这样其效果要比 PixelRNN 快很多，但是依然不够快。

![Untitled](/assets/notes/deep-learning/generative-models/Untitled%209.png)

![Untitled](/assets/notes/deep-learning/generative-models/Untitled%2010.png)

## 3. AutoEncoders 自编码器

> 参考：
> 
> - 网上的一个简介，解释的很详细，作图也很好：[https://towardsdatascience.com/a-wizards-guide-to-adversarial-autoencoders-part-1-autoencoder-d9a5f8795af4](https://towardsdatascience.com/a-wizards-guide-to-adversarial-autoencoders-part-1-autoencoder-d9a5f8795af4)
> - 另一个简介，似乎是来自同一个作者：[https://towardsdatascience.com/auto-encoder-what-is-it-and-what-is-it-used-for-part-1-3e5c6f017726](https://towardsdatascience.com/auto-encoder-what-is-it-and-what-is-it-used-for-part-1-3e5c6f017726)

### 3.1 AutoEncoders 简介

AutoEncoders 是无监督学习（unsupervised learning）中的一个概念。它是一个神经网络，它用于训练并预测一个结果，使得该结果和输入非常接近。即，它其实是用来预测输入本身，因为它并不需要 groundtruth label 作输入。

**An Autoencoder is a neural network that is trained to produce an output which is very similar to its input** (so it basically attempts to copy its input to its output) and since it doesn’t need any targets (labels), it can be trained in an unsupervised manner.

![Untitled](/assets/notes/deep-learning/generative-models/Untitled%2011.png)

![Untitled](/assets/notes/deep-learning/generative-models/Untitled%2012.png)

一个 Autoencoder 通常包括两个部分：

**?1?Encoder 编码器**。编码器的作用可以是降维，也可以是升维（通常都是降维），即它的输入是原始数据，而输出是一个原始数据的**低维的”编码“**，通常被称为 **Latent Code**。这个过程可以用一个函数表示：

$$
h=q(x)
$$

**?2?Decoder 解码器**。解码器的作用自然是从编码中还原一个和原始输入接近的输出结果。通常它的输出的维度和输入完全一致（毕竟是为了还原输入）。用另一个函数表示：

$$
x\_=p(h)
$$

AutoEncoders 的另一个常见用途是用于 Supervised training 中，例如当AutoEncoders训练完成后，可以直接扔掉 Decoders，只使用 Encoders，然后可以将 Latent Code z 后面接上 classifier 后，用于做 data labeling 数据分类。这是早期很常见的用法。当然通常还是需要针对新的数据来 fine-tune encoder 了。

![Untitled](/assets/notes/deep-learning/generative-models/Untitled%2013.png)

不难看出，这种 General AutoEncoders **显然只能重建出训练集中的数据**，因为它的 Encoded Latent Code z 完全来自训练数据集编码后的结果。那么如何重建出不在训练集中的数据呢？这就需要使用 Variational AutoEncodes (VAE) 了，参见后面内容。

### 3.2 Target Loss Function

![Untitled](/assets/notes/deep-learning/generative-models/Untitled%2014.png)

根据输入不同，主要是两种 loss：

1. **如果输入是 binary input，则使用 Cross-entroy loss。**

例如，输入是 binary image（例如 MNIST 数据集）。

从上图中给出的公式，如果 $x_k=1$，那么第 1 项是 0，此时 loss 等于 $\log(1 - \hat{x}_k)$ 显然当 $\hat{x}_t$ 越小，整个 loss 越小。反之，如果 $x_k=0$，能够推出此时 $\hat{x}_t$ 应当越大才使得 loss 越小。

不过注意，此时它的输出依然是连续的。此时输出的每个值可以代表一个概率，再经过一次后处理就能还原出和输入一样的 binary 形式。例如，如果是 0.9，就认为是非常接近 1，而把这个位置最终设为 1；反之如果接近于 0，则就设为 0。

1. **如果输入是连续值数据，那么使用 MSE Loss。**

这个没太多好说的，MSE loss 很直接。

### 3.3 AutoEncoders 和 PCA 对比

> **参考**：
[http://www.cs.toronto.edu/~rgrosse/courses/csc411_f18/slides/lec12-slides.pdf](http://www.cs.toronto.edu/~rgrosse/courses/csc411_f18/slides/lec12-slides.pdf)
这是来自多伦多大学的 CSC 411 课程 Machine Learning and Data Mining 的课件（课程链接：[http://www.cs.toronto.edu/~rgrosse/courses/csc411_f18/）。](http://www.cs.toronto.edu/~rgrosse/courses/csc411_f18/）。)
> 

整体上 AutoEncoders 比 PCA 在降维重建这块要好。这是因为 PCA 是纯线性变换，而 AutoEncoders 是非线性的（体现在它使用例如 Sigmoid 之类的激活函数）。实际上，**如果** AutoEncoders 中的 Encoder 函数 f(x) 和 Decoders 函数 g(h) 全都是线性函数的话，可以证明，它的最优解就是 PCA。

![Untitled](/assets/notes/deep-learning/generative-models/Untitled%2015.png)

<div class="note-index-list">
  <a class="note-index-card" href="/deep-learning/generative-models-1-vae/">
    <strong>Generative Models 1: VAE</strong>
    <span>AutoEncoders, VAE intuition, ELBO derivation, loss terms, reparameterization trick, Conv-VAE, and VQ-VAE references.</span>
  </a>
  <a class="note-index-card" href="/deep-learning/generative-models-2-gan/">
    <strong>Generative Models 2: GAN</strong>
    <span>GAN intuition, adversarial objective, alternating training, generator/discriminator structure, and PyTorch implementation flow.</span>
  </a>
</div>
