import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins:[react()],
  server:{proxy:{'/api':'http://localhost:8012','/health':'http://localhost:8012','/uploads':'http://localhost:8012'}},
});
