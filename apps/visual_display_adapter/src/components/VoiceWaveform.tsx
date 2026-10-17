type VoiceWaveformProps = {
  active: boolean;
};

const BARS = [18, 34, 52, 28, 64, 40, 22, 58, 36, 48, 26, 62, 32, 44, 20];

export function VoiceWaveform({ active }: VoiceWaveformProps) {
  return (
    <div className="flex h-12 items-end gap-[3px]" aria-hidden>
      {BARS.map((height, index) => (
        <span
          key={index}
          className={`voice-bar w-[5px] rounded-full ${active ? "voice-bar-live" : "opacity-40"}`}
          style={{
            height: `${height}px`,
            animationDelay: `${index * 70}ms`,
            background: index % 3 === 0 ? "#10B981" : "#00E5FF",
          }}
        />
      ))}
    </div>
  );
}
