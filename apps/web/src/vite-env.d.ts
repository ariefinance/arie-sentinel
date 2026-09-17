/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_AUTH_MODE?: 'development' | 'production';
  readonly VITE_DEMO_LABEL?: string;
  readonly VITE_DEV_ROLE?: 'analyst' | 'manager';
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
