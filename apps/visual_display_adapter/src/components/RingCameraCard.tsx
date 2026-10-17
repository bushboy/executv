import { Camera, Truck } from "lucide-react";

import { CAMERA_SNAPSHOT, type AlertItem } from "../types/visual";

type RingCameraCardProps = {
  event?: AlertItem;
};

export function RingCameraCard({ event }: RingCameraCardProps) {
  const snapshot = event?.image_url || CAMERA_SNAPSHOT;
  const location = event?.location ?? "Waiting for the camera feed";
  const description = event?.description ?? "The live frame arrives with the briefing.";

  return (
    <div className="relative overflow-hidden rounded-2xl">
      <img
        src={snapshot}
        alt={location}
        className="h-[220px] w-full object-cover brightness-90 contrast-110"
      />
      <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/20 to-transparent" />
      <div className="absolute top-4 left-4 flex items-center gap-2 rounded-full border border-rose-500/40 bg-rose-500/20 px-3 py-1.5 backdrop-blur-md">
        <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-rose-500 shadow-[0_0_12px_#F43F5E]" />
        <span className="text-[11px] font-black tracking-[0.16em] text-rose-100 uppercase">Live camera</span>
      </div>
      <div className="absolute top-[34%] left-[18%] h-[32%] w-[48%] rounded-md border-2 border-[#00E5FF] shadow-[0_0_18px_rgba(0,229,255,0.55)]">
        <div className="absolute -bottom-8 left-0 flex max-w-[140%] items-center gap-2 rounded-md bg-slate-950/90 px-2.5 py-1 text-[11px] font-bold tracking-wide text-[#00E5FF] uppercase">
          <Truck className="h-3.5 w-3.5 shrink-0" />
          {location}
        </div>
      </div>
      <div className="absolute right-4 bottom-4 left-4">
        <div className="mb-1 flex items-center gap-2 text-xs font-bold tracking-[0.18em] text-cyan-300 uppercase">
          <Camera className="h-4 w-4" />
          Ring site gateway
        </div>
        <p className="text-lg font-bold text-white">{location}</p>
        <p className="text-sm text-slate-300">{description}</p>
      </div>
    </div>
  );
}
