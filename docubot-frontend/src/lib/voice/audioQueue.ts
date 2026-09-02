/**
 * AudioQueue - Web Audio API streaming audio player with instant barge-in flushing
 * and master AnalyserNode volume measurement for visualizer animations.
 */

export class AudioQueue {
  private ctx: AudioContext | null = null;
  private nextPlayTime: number = 0;
  private sources: AudioBufferSourceNode[] = [];
  private isPlaying: boolean = false;
  private audioBufferQueue: ArrayBuffer[] = [];
  private analyser: AnalyserNode | null = null;
  private onEndedCallback: (() => void) | null = null;

  constructor() {
    // AudioContext initialized lazily or on first user click
  }

  public async initContext(): Promise<void> {
    if (typeof window === "undefined") return;
    try {
      if (!this.ctx) {
        const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
        this.ctx = new AudioCtx();
      }
      if (this.ctx && this.ctx.state === "suspended") {
        await this.ctx.resume();
      }
    } catch (err) {
      console.warn("[AudioQueue] AudioContext initialization:", err);
    }
  }

  /**
   * Enqueues a base64-encoded audio chunk for gapless playback.
   */
  public async enqueueBase64(base64Data: string): Promise<void> {
    await this.initContext();
    if (!this.ctx) return;

    try {
      const binaryString = window.atob(base64Data);
      const len = binaryString.length;
      const bytes = new Uint8Array(len);
      for (let i = 0; i < len; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }

      const arrayBuffer = bytes.buffer;
      this.audioBufferQueue.push(arrayBuffer);
      this.processQueue();
    } catch (e) {
      console.error("[AudioQueue] Failed to decode and enqueue base64 audio:", e);
    }
  }

  /**
   * Enqueues an ArrayBuffer audio chunk for playback.
   */
  public async enqueue(arrayBuffer: ArrayBuffer): Promise<void> {
    await this.initContext();
    if (!this.ctx) return;

    this.audioBufferQueue.push(arrayBuffer);
    this.processQueue();
  }

  private async processQueue(): Promise<void> {
    if (this.isPlaying || this.audioBufferQueue.length === 0 || !this.ctx) return;

    this.isPlaying = true;
    const arrayBuffer = this.audioBufferQueue.shift();
    if (!arrayBuffer) {
      this.isPlaying = false;
      return;
    }

    try {
      if (this.ctx.state === "suspended") {
        await this.ctx.resume();
      }
      const audioBuffer = await this.ctx.decodeAudioData(arrayBuffer.slice(0));
      this.playBuffer(audioBuffer);
    } catch (e) {
      console.error("[AudioQueue] Error decoding audio data:", e);
      this.isPlaying = false;
      this.processQueue();
    }
  }

  public setOnEnded(cb: () => void): void {
    this.onEndedCallback = cb;
  }

  private playBuffer(buffer: AudioBuffer): void {
    if (!this.ctx) return;

    const source = this.ctx.createBufferSource();
    source.buffer = buffer;

    if (!this.analyser) {
      this.analyser = this.ctx.createAnalyser();
      this.analyser.fftSize = 256;
    }

    source.connect(this.analyser);
    this.analyser.connect(this.ctx.destination);

    // Schedule play time to ensure gapless streaming
    const now = this.ctx.currentTime;
    let startTime = now;

    if (this.nextPlayTime > now) {
      startTime = this.nextPlayTime;
    }

    source.start(startTime);
    this.nextPlayTime = startTime + buffer.duration;
    this.sources.push(source);

    source.onended = () => {
      this.sources = this.sources.filter((s) => s !== source);
      this.isPlaying = false;

      // If queue is empty and all playing finished, reset schedule clock
      if (this.sources.length === 0 && this.audioBufferQueue.length === 0) {
        this.nextPlayTime = 0;
        if (this.onEndedCallback) {
          this.onEndedCallback();
        }
      }

      this.processQueue();
    };
  }

  /**
   * Instantly stops all current and queued audio playback (Barge-in).
   */
  public interrupt(): void {
    this.sources.forEach((source) => {
      try {
        source.stop();
        source.disconnect();
      } catch {
        // Source may have already stopped or not started
      }
    });

    this.sources = [];
    this.audioBufferQueue = [];
    this.nextPlayTime = 0;
    this.isPlaying = false;
  }

  public stopAndFlush(): void {
    this.interrupt();
  }

  /**
   * Resumes the AudioContext if suspended.
   */
  public resume(): void {
    if (this.ctx && this.ctx.state === "suspended") {
      this.ctx.resume().catch(() => {});
    }
  }

  /**
   * Returns current RMS volume level of playing audio (0.0 to 1.0) for visualizer.
   */
  public getVolumeLevel(): number {
    if (!this.ctx || !this.analyser || !this.isPlaying) return 0;

    const bufferLength = this.analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    this.analyser.getByteTimeDomainData(dataArray);

    let sum = 0;
    for (let i = 0; i < bufferLength; i++) {
      const val = (dataArray[i] - 128) / 128;
      sum += val * val;
    }
    return Math.sqrt(sum / bufferLength);
  }

  public get playing(): boolean {
    return this.isPlaying;
  }
}
