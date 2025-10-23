import { getJSON } from "./http";
const B = "/api/search";
export const fetchSummary     = () => getJSON(`${B}/summary`);
export const fetchVideos      = () => getJSON(`${B}/videos`);
export const fetchVideo       = (id: string) => getJSON(`${B}/videos/${id}`);
export const fetchVideoFrames = (id: string, a?: any) => getJSON(`${B}/videos/${id}/frames`, a);
export const searchOCR        = (q: string, a?: any) => getJSON(`${B}/search`, { q, ...a });
