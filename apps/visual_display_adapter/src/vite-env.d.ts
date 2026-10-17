/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_CORE_ENGINE_URL: string;
  readonly VITE_INGRESS_GATEWAY_URL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
