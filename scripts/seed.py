"""Seed the catalog with canonical, well-known entries (run once; idempotent overwrite).

Builds Entry objects through the schema (so ids/dedup are canonical) and writes the data
files. Re-running regenerates the seed set. The weekly agent grows the catalog from here.

    uv run python scripts/seed.py
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.schema import Entry  # noqa: E402
from pipeline import db  # noqa: E402

SEED_DATE = dt.date(2026, 6, 13)

# (title, area, task, kind, links, year, tags, summary)
SEEDS: list[dict] = [
    # ---------------- Image & 2D Art ----------------
    dict(title="Stable Diffusion XL", area="image-2d", task="text-to-image", kind="oss",
         links={"arxiv": "https://arxiv.org/abs/2307.01952",
                "github": "https://github.com/Stability-AI/generative-models"},
         year=2023, tags=["diffusion", "open-weights"],
         summary="A latent text-to-image diffusion model with a larger UNet and refiner stage; the open-weights backbone for most game/anime concept-art LoRA ecosystems."),
    dict(title="ControlNet", area="image-2d", task="controlnet", kind="oss",
         links={"arxiv": "https://arxiv.org/abs/2302.05543",
                "github": "https://github.com/lllyasviel/ControlNet"},
         year=2023, tags=["conditioning", "pose", "depth"],
         summary="Adds spatial conditioning (edges, depth, pose, scribbles) to diffusion models, enabling layout- and sketch-controlled generation central to production art workflows."),
    dict(title="Real-ESRGAN", area="image-2d", task="super-resolution", kind="oss",
         links={"arxiv": "https://arxiv.org/abs/2107.10833",
                "github": "https://github.com/xinntao/Real-ESRGAN"},
         year=2021, tags=["upscaling", "anime", "restoration"],
         summary="A practical blind super-resolution model with a dedicated anime model variant, widely used to upscale textures and anime frames while preserving line sharpness."),
    dict(title="waifu2x", area="image-2d", task="super-resolution", kind="oss",
         links={"github": "https://github.com/nagadomi/waifu2x"},
         year=2015, tags=["anime", "upscaling"],
         summary="A CNN-based super-resolution and denoiser specialized for anime-style art, the long-standing baseline for upscaling illustrations and anime stills."),
    dict(title="Anime2Sketch", area="image-2d", task="lineart-extraction", kind="oss",
         links={"github": "https://github.com/Mukosame/Anime2Sketch"},
         year=2021, tags=["lineart", "anime"],
         summary="A sketch extractor that produces clean line art from anime and illustration images, useful for reference, retracing, and colorization pipelines."),
    dict(title="NovelAI Image Generation", area="image-2d", task="anime-character-design", kind="proprietary",
         links={"website": "https://novelai.net/"},
         year=2022, tags=["anime", "character", "commercial", "api"],
         summary="A commercial anime-focused image generator with character-consistency tooling, popular for character design and reference sheets in indie anime production."),
    dict(title="Midjourney", area="image-2d", task="text-to-image", kind="proprietary",
         links={"website": "https://www.midjourney.com/"},
         tags=["commercial", "concept-art"],
         summary="A commercial text-to-image service known for high aesthetic quality, widely used for rapid concept-art ideation across game and anime studios."),

    # ---------------- 3D Generation ----------------
    dict(title="DreamFusion: Text-to-3D using 2D Diffusion", area="gen-3d", task="text-to-3d", kind="oss",
         links={"arxiv": "https://arxiv.org/abs/2209.14988", "project": "https://dreamfusion3d.github.io/"},
         year=2022, tags=["diffusion", "score-distillation"],
         summary="Introduces score distillation sampling to optimize a NeRF from a pretrained 2D diffusion model, generating 3D objects from text with no 3D training data."),
    dict(title="Instant Neural Graphics Primitives (Instant-NGP)", area="gen-3d", task="mesh-generation", kind="oss",
         links={"arxiv": "https://arxiv.org/abs/2201.05989", "github": "https://github.com/NVlabs/instant-ngp"},
         year=2022, tags=["nerf", "hash-encoding"],
         summary="A multiresolution hash encoding that trains NeRFs and neural fields in seconds, a foundational speedup behind many image-to-3D reconstruction pipelines."),
    dict(title="3D Gaussian Splatting for Real-Time Radiance Field Rendering", area="gen-3d",
         task="mesh-generation", kind="oss",
         links={"arxiv": "https://arxiv.org/abs/2308.04079",
                "github": "https://github.com/graphdeco-inria/gaussian-splatting"},
         year=2023, tags=["gaussian-splatting", "real-time"],
         summary="Represents scenes as optimized 3D Gaussians for real-time, high-quality radiance-field rendering, now a dominant representation for captured 3D assets."),
    dict(title="GET3D", area="gen-3d", task="mesh-generation", kind="oss",
         links={"arxiv": "https://arxiv.org/abs/2209.11163", "github": "https://github.com/nv-tlabs/GET3D"},
         year=2022, tags=["textured-mesh", "gan"],
         summary="A generative model that produces textured 3D meshes with complex topology directly, aimed at game-ready asset generation."),
    dict(title="Meshy", area="gen-3d", task="image-to-3d", kind="proprietary",
         links={"website": "https://www.meshy.ai/"},
         tags=["commercial", "texture", "auto-rig", "api"],
         summary="A commercial text/image-to-3D service producing game-ready textured meshes with PBR and auto-rigging; credit-based API and web app widely used in indie pipelines."),
    dict(title="Tripo", area="gen-3d", task="text-to-3d", kind="proprietary",
         links={"website": "https://www.tripo3d.ai/"},
         tags=["commercial", "fast", "api"],
         summary="A commercial text/image-to-3D generator known for fast mesh creation, frequently used for rapid game asset prototyping."),
    dict(title="Rodin (Hyper3D)", area="gen-3d", task="text-to-3d", kind="proprietary",
         links={"website": "https://hyper3d.ai/"},
         tags=["commercial", "api"],
         summary="A commercial 3D generation service with an API producing detailed textured models from text or images for production asset workflows."),

    # ---------------- Characters & Avatars ----------------
    dict(title="AvatarCLIP", area="characters", task="avatar-generation", kind="oss",
         links={"arxiv": "https://arxiv.org/abs/2205.08535", "github": "https://github.com/hongfz16/AvatarCLIP"},
         year=2022, tags=["text-driven", "avatar"],
         summary="Zero-shot text-driven generation and animation of 3D avatars by guiding a neural human model with CLIP, an early framework for describable digital humans."),
    dict(title="RigNet: Neural Rigging for Articulated Characters", area="characters", task="auto-rigging", kind="oss",
         links={"arxiv": "https://arxiv.org/abs/2005.00559", "github": "https://github.com/zhan-xu/RigNet"},
         year=2020, tags=["rigging", "skeleton"],
         summary="Predicts an animation skeleton and skinning weights directly from a 3D character mesh, automating a traditionally manual rigging step."),
    dict(title="MetaHuman Creator", area="characters", task="avatar-generation", kind="proprietary",
         links={"website": "https://www.unrealengine.com/en-US/metahuman"},
         tags=["commercial", "unreal", "rigged"],
         summary="Epic's tool for creating fully rigged, photorealistic digital humans for Unreal Engine, an industry standard for game character and cinematic avatars."),
    dict(title="Mixamo", area="characters", task="auto-rigging", kind="proprietary",
         links={"website": "https://www.mixamo.com/"},
         tags=["commercial", "auto-rig", "animation-library"],
         summary="Adobe's free service that auto-rigs uploaded humanoid meshes and applies a large motion library, a staple for quickly animating game characters."),

    # ---------------- Animation & Motion ----------------
    dict(title="RIFE: Real-Time Intermediate Flow Estimation", area="animation", task="inbetweening", kind="oss",
         links={"arxiv": "https://arxiv.org/abs/2011.06294",
                "github": "https://github.com/hzwer/ECCV2022-RIFE"},
         year=2022, tags=["interpolation", "real-time"],
         summary="A fast flow-based frame interpolation model, widely used (with anime-tuned variants) to generate in-between frames and smooth low-frame-rate animation."),
    dict(title="AnimeInterp: Deep Animation Video Interpolation", area="animation", task="inbetweening", kind="oss",
         links={"arxiv": "https://arxiv.org/abs/2104.06642",
                "github": "https://github.com/lisiyao21/AnimeInterp"},
         year=2021, tags=["anime", "interpolation"],
         summary="Segment-guided frame interpolation designed for the flat colors and large motions of cartoon/anime, addressing failure modes of photoreal interpolators."),
    dict(title="ToonCrafter: Generative Cartoon Interpolation", area="animation", task="inbetweening", kind="oss",
         links={"arxiv": "https://arxiv.org/abs/2405.17933",
                "github": "https://github.com/Doubiiu/ToonCrafter"},
         year=2024, tags=["anime", "diffusion", "interpolation"],
         summary="Diffusion-based generative interpolation that synthesizes in-between frames for cartoon/anime keyframes, handling large non-linear motion and occlusion."),
    dict(title="Human Motion Diffusion Model (MDM)", area="animation", task="text-to-motion", kind="oss",
         links={"arxiv": "https://arxiv.org/abs/2209.14916",
                "github": "https://github.com/GuyTevet/motion-diffusion-model"},
         year=2022, tags=["motion-generation", "diffusion"],
         summary="A lightweight diffusion model that generates human motion from text or actions, a common baseline for text-to-motion in animation research."),
    dict(title="DeepMotion (Animate 3D)", area="animation", task="video-mocap", kind="proprietary",
         links={"website": "https://www.deepmotion.com/"},
         tags=["commercial", "markerless-mocap", "api"],
         summary="A commercial markerless motion-capture service that converts ordinary video into 3D animation (FBX/BVH/GLB), enabling mocap without a suit or studio."),
    dict(title="Move.ai", area="animation", task="video-mocap", kind="proprietary",
         links={"website": "https://www.move.ai/"},
         tags=["commercial", "markerless-mocap", "api"],
         summary="A markerless multi-camera motion-capture service producing high-quality 3D motion from standard cameras, used by indie and mid-size studios."),
    dict(title="Cascadeur", area="animation", task="physics-animation", kind="proprietary",
         links={"website": "https://cascadeur.com/"},
         tags=["commercial", "physics", "keyframe"],
         summary="A physics-aware keyframe animation tool with AI auto-posing and interpolation, designed for believable character action animation."),

    # ---------------- Video ----------------
    dict(title="Stable Video Diffusion", area="video", task="image-to-video", kind="oss",
         links={"arxiv": "https://arxiv.org/abs/2311.15127",
                "github": "https://github.com/Stability-AI/generative-models"},
         year=2023, tags=["diffusion", "open-weights"],
         summary="An open-weights latent video diffusion model for image-to-video and short clip generation, a base for anime/game motion experiments and fine-tunes."),
    dict(title="Segment Anything Model 2 (SAM 2)", area="video", task="rotoscoping", kind="oss",
         links={"arxiv": "https://arxiv.org/abs/2408.00714",
                "github": "https://github.com/facebookresearch/sam2"},
         year=2024, tags=["segmentation", "matting", "tracking"],
         summary="A promptable segmentation model that tracks objects across video frames, the backbone of modern AI-assisted rotoscoping and matting tools."),
    dict(title="AnimateDiff", area="video", task="text-to-video", kind="oss",
         links={"arxiv": "https://arxiv.org/abs/2307.04725",
                "github": "https://github.com/guoyww/AnimateDiff"},
         year=2023, tags=["diffusion", "motion-module"],
         summary="Adds a plug-in motion module to personalized text-to-image diffusion models, animating existing image checkpoints and LoRAs into short clips."),
    dict(title="Runway Gen", area="video", task="text-to-video", kind="proprietary",
         links={"website": "https://runwayml.com/"},
         tags=["commercial", "video-generation", "api"],
         summary="A commercial text/image-to-video generation and editing suite used for previs, motion design, and stylized video in production."),
    dict(title="Pika", area="video", task="text-to-video", kind="proprietary",
         links={"website": "https://pika.art/"},
         tags=["commercial", "video-generation"],
         summary="A commercial video generation tool for text- and image-driven short clips, including anime-aware styles."),

    # ---------------- Audio ----------------
    dict(title="VITS", area="audio", task="tts", kind="oss",
         links={"arxiv": "https://arxiv.org/abs/2106.06103",
                "github": "https://github.com/jaywalnut310/vits"},
         year=2021, tags=["tts", "end-to-end"],
         summary="An end-to-end text-to-speech model combining variational inference and adversarial training, the basis for many open Japanese and character TTS voices."),
    dict(title="MusicGen (AudioCraft)", area="audio", task="music-bgm", kind="oss",
         links={"arxiv": "https://arxiv.org/abs/2306.05284",
                "github": "https://github.com/facebookresearch/audiocraft"},
         year=2023, tags=["music-generation", "open-weights"],
         summary="A single-stage controllable music generation model conditioned on text and melody, used for prototyping background music and adaptive scoring."),
    dict(title="RVC (Retrieval-based Voice Conversion)", area="audio", task="voice-cloning", kind="oss",
         links={"github": "https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI"},
         year=2023, tags=["voice-conversion", "open-source"],
         summary="A popular open-source voice-conversion toolkit that retargets a source voice to a trained timbre, widely used for character voice and dubbing experiments."),
    dict(title="ElevenLabs", area="audio", task="tts", kind="proprietary",
         links={"website": "https://elevenlabs.io/"},
         tags=["commercial", "voice-cloning", "dubbing", "api"],
         summary="A commercial speech platform offering expressive TTS, voice cloning, dubbing, and sound effects, broadly adopted for game and animation voice-over."),
    dict(title="Synthesizer V", area="audio", task="singing-voice", kind="proprietary",
         links={"website": "https://dreamtonics.com/synthesizerv/"},
         tags=["commercial", "singing-synthesis"],
         summary="A commercial singing voice synthesizer with expressive control, a leading tool for anime-style vocal and song production."),
    dict(title="Suno", area="audio", task="music-bgm", kind="proprietary",
         links={"website": "https://suno.com/"},
         tags=["commercial", "music-generation", "api"],
         summary="A commercial music generation service producing full songs with vocals from text prompts, used for rapid soundtrack and BGM prototyping."),

    # ---------------- Text, Narrative & Design ----------------
    dict(title="LLaMA", area="text-design", task="npc-dialogue", kind="oss",
         links={"arxiv": "https://arxiv.org/abs/2302.13971",
                "github": "https://github.com/meta-llama/llama"},
         year=2023, tags=["llm", "open-weights"],
         summary="A family of open foundation language models commonly fine-tuned for NPC dialogue, narrative drafting, and in-game text systems."),
    dict(title="Whisper", area="text-design", task="localization", kind="oss",
         links={"arxiv": "https://arxiv.org/abs/2212.04356",
                "github": "https://github.com/openai/whisper"},
         year=2022, tags=["asr", "transcription"],
         summary="A robust multilingual speech-recognition model used in localization pipelines for transcription and as a front-end to translation and dubbing."),
    dict(title="Mistral 7B", area="text-design", task="narrative-quest", kind="oss",
         links={"arxiv": "https://arxiv.org/abs/2310.06825",
                "github": "https://github.com/mistralai/mistral-src"},
         year=2023, tags=["llm", "open-weights"],
         summary="An efficient open-weights language model frequently used for narrative, quest, and design-document drafting in game writing tools."),
    dict(title="Inworld AI", area="text-design", task="npc-dialogue", kind="proprietary",
         links={"website": "https://inworld.ai/"},
         tags=["commercial", "npc", "memory", "api"],
         summary="A commercial platform for building AI NPCs with persistent memory and unscripted dialogue, integrating with major game engines."),
    dict(title="DeepL", area="text-design", task="localization", kind="proprietary",
         links={"website": "https://www.deepl.com/"},
         tags=["commercial", "translation", "api"],
         summary="A commercial neural machine translation service with an API, used in game/anime localization for high-quality first-pass translation."),

    # ---------------- Manga & Comics ----------------
    dict(title="The Manga Whisperer (Magi)", area="manga", task="panel-layout", kind="oss",
         links={"arxiv": "https://arxiv.org/abs/2401.10224",
                "github": "https://github.com/ragavsachdeva/magi"},
         year=2024, tags=["manga", "detection", "transcription"],
         summary="Detects panels, characters, and text in manga pages and generates an ordered transcript, supporting layout analysis and accessibility/translation tooling."),
    dict(title="Jenova AI Manga Generator", area="manga", task="manga-generation", kind="proprietary",
         links={"website": "https://www.jenova.ai/"},
         tags=["commercial", "manga", "panels"],
         summary="A commercial tool that generates manga pages and panels with character consistency from prompts, aimed at sequential-art creation without drawing."),
]


# Japanese summaries, keyed by title (injected into the seeds at build time).
SUMMARIES_JA: dict[str, str] = {
    "Stable Diffusion XL": "より大きなUNetとリファイナー段を備えた潜在拡散によるテキスト→画像モデル。ゲーム・アニメのコンセプトアート向けLoRAエコシステムの基盤となるオープンウェイトのバックボーン。",
    "ControlNet": "エッジ・深度・ポーズ・線画などの空間的条件付けを拡散モデルに追加し、レイアウトやスケッチで制御した生成を可能にする。制作ワークフローの中核技術。",
    "Real-ESRGAN": "実用的なブラインド超解像モデル。アニメ専用モデルも提供され、線のシャープさを保ちつつテクスチャやアニメフレームのアップスケールに広く使われる。",
    "waifu2x": "アニメ調イラストに特化したCNNベースの超解像・ノイズ除去。イラストやアニメ静止画のアップスケールにおける定番のベースライン。",
    "Anime2Sketch": "アニメやイラスト画像からきれいな線画を抽出するツール。参照・トレース・着色のパイプラインに役立つ。",
    "NovelAI Image Generation": "キャラクターの一貫性を保つ機能を備えた商用のアニメ特化型画像生成サービス。インディーのアニメ制作でキャラクターデザインや設定画によく使われる。",
    "Midjourney": "高い美的品質で知られる商用のテキスト→画像サービス。ゲーム・アニメ制作で素早いコンセプトアートの発想に広く利用される。",
    "DreamFusion: Text-to-3D using 2D Diffusion": "スコア蒸留サンプリングを導入し、学習済みの2D拡散モデルからNeRFを最適化。3D学習データなしでテキストから3D物体を生成する。",
    "Instant Neural Graphics Primitives (Instant-NGP)": "マルチ解像度ハッシュエンコーディングによりNeRFやニューラルフィールドを数秒で学習。多くの画像→3D再構成パイプラインの基盤となる高速化技術。",
    "3D Gaussian Splatting for Real-Time Radiance Field Rendering": "シーンを最適化された3Dガウシアンで表現し、リアルタイムかつ高品質な放射輝度場レンダリングを実現。撮影した3Dアセットの主要表現として普及。",
    "GET3D": "複雑なトポロジーを持つテクスチャ付き3Dメッシュを直接生成する生成モデル。ゲームで使えるアセット生成を目指す。",
    "Meshy": "PBRと自動リギングに対応し、ゲームで使えるテクスチャ付きメッシュを生成する商用のテキスト/画像→3Dサービス。APIとWebアプリを提供し、インディー制作で広く使われる。",
    "Tripo": "高速なメッシュ生成で知られる商用のテキスト/画像→3Dジェネレーター。ゲームアセットの迅速なプロトタイピングによく使われる。",
    "Rodin (Hyper3D)": "テキストや画像から詳細なテクスチャ付きモデルを生成する、API付きの商用3D生成サービス。",
    "AvatarCLIP": "CLIPでニューラル人体モデルを誘導し、テキストからゼロショットで3Dアバターを生成・アニメーション化する初期のフレームワーク。",
    "RigNet: Neural Rigging for Articulated Characters": "3Dキャラクターメッシュから、アニメーション用のスケルトンとスキニングウェイトを直接予測し、従来は手作業だったリギングを自動化する。",
    "MetaHuman Creator": "Unreal Engine向けに、フルリグ済みでフォトリアルなデジタルヒューマンを作成するEpicのツール。ゲームのキャラクターや映像表現の業界標準。",
    "Mixamo": "アップロードした人型メッシュを自動リギングし、豊富なモーションライブラリを適用できるAdobeの無料サービス。ゲームキャラの即時アニメーション化の定番。",
    "RIFE: Real-Time Intermediate Flow Estimation": "高速なフローベースのフレーム補間モデル。アニメ向け調整版とともに、中割りフレーム生成や低フレームレートアニメの滑らか化に広く使われる。",
    "AnimeInterp: Deep Animation Video Interpolation": "平坦な色と大きな動きを持つカートゥーン/アニメ向けに設計された、セグメント誘導のフレーム補間。実写向け補間の弱点に対処する。",
    "ToonCrafter: Generative Cartoon Interpolation": "カートゥーン/アニメのキーフレーム間の中割りフレームを合成する拡散ベースの生成的補間。大きな非線形の動きやオクルージョンに対応。",
    "Human Motion Diffusion Model (MDM)": "テキストや動作から人体モーションを生成する軽量な拡散モデル。アニメーション研究におけるテキスト→モーションの定番ベースライン。",
    "DeepMotion (Animate 3D)": "通常の動画を3Dアニメーション（FBX/BVH/GLB）に変換する商用のマーカーレスモーションキャプチャサービス。スーツやスタジオなしでmocapを実現。",
    "Move.ai": "標準的なカメラから高品質な3Dモーションを生成するマーカーレスのマルチカメラmocapサービス。インディーから中規模スタジオで利用される。",
    "Cascadeur": "AIによる自動ポーズ付けと補間を備えた物理対応のキーフレームアニメーションツール。説得力のあるキャラクターアクションの制作向け。",
    "Stable Video Diffusion": "画像→動画や短尺クリップ生成に対応するオープンウェイトの潜在動画拡散モデル。アニメ・ゲームのモーション実験やファインチューンの土台。",
    "Segment Anything Model 2 (SAM 2)": "プロンプト可能なセグメンテーションモデルで、動画フレーム間で対象を追跡する。現代のAIロトスコープやマッティングツールの基盤。",
    "AnimateDiff": "パーソナライズしたテキスト→画像拡散モデルにモーションモジュールを追加し、既存のチェックポイントやLoRAを短尺クリップにアニメーション化する。",
    "Runway Gen": "プレビズ、モーションデザイン、スタイライズ動画に使われる商用のテキスト/画像→動画の生成・編集スイート。",
    "Pika": "テキストや画像から短尺クリップを生成する商用動画ツール。アニメ調のスタイルにも対応。",
    "VITS": "変分推論と敵対的学習を組み合わせたエンドツーエンドの音声合成モデル。多くのオープンな日本語・キャラクター音声の基盤。",
    "MusicGen (AudioCraft)": "テキストやメロディで条件付けする単一段階の制御可能な音楽生成モデル。BGMのプロトタイピングや適応的スコアリングに使われる。",
    "RVC (Retrieval-based Voice Conversion)": "ソース音声を学習済みの声質に変換する人気のオープンソース声質変換ツールキット。キャラクターボイスやダビングの実験に広く使われる。",
    "ElevenLabs": "表現力豊かなTTS、ボイスクローン、ダビング、効果音を提供する商用音声プラットフォーム。ゲーム・アニメのボイスオーバーで広く採用されている。",
    "Synthesizer V": "表現を細かく制御できる商用の歌声合成ソフト。アニメ調のボーカルや楽曲制作の主要ツール。",
    "Suno": "テキストからボーカル付きの楽曲をまるごと生成する商用音楽生成サービス。サウンドトラックやBGMの迅速なプロトタイピングに使われる。",
    "LLaMA": "NPC対話、物語の下書き、ゲーム内テキストシステム向けによくファインチューンされる、オープンな基盤言語モデル群。",
    "Whisper": "頑健な多言語音声認識モデル。文字起こしや、翻訳・ダビングの前段として、ローカライズのパイプラインで使われる。",
    "Mistral 7B": "効率的なオープンウェイトの言語モデル。ゲームの物語・クエスト・設計文書の下書きツールで広く使われる。",
    "Inworld AI": "永続的な記憶と非定型の対話を備えたAI NPCを構築する商用プラットフォーム。主要なゲームエンジンと連携する。",
    "DeepL": "API付きの商用ニューラル機械翻訳サービス。ゲーム・アニメのローカライズで高品質な初稿翻訳に使われる。",
    "The Manga Whisperer (Magi)": "漫画ページからコマ・キャラクター・テキストを検出し、順序付きの書き起こしを生成する。レイアウト解析やアクセシビリティ・翻訳ツールを支える。",
    "Jenova AI Manga Generator": "プロンプトからキャラクターの一貫性を保ちつつ漫画ページやコマを生成する商用ツール。作画なしのシーケンシャルアート制作を目指す。",
}


def build() -> list[Entry]:
    out = []
    for s in SEEDS:
        data = dict(s)
        ja = SUMMARIES_JA.get(data["title"])
        if ja:
            data["summary_ja"] = ja
        out.append(Entry(source="seed", date_added=SEED_DATE, **data))
    return out


def main() -> int:
    entries = build()
    db.save_split(entries)
    oss = sum(1 for e in entries if e.kind == "oss")
    prop = len(entries) - oss
    print(f"seeded {len(entries)} entries ({oss} oss, {prop} proprietary) into data/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
