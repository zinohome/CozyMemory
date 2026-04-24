import type { HTTP } from "../http.js";
import type {
  AddKnowledgeResponse,
  CognifyResponse,
  DatasetInfo,
  DatasetListResponse,
  DeleteResponse,
  KnowledgeSearchResponse,
} from "../types.js";

export class Knowledge {
  constructor(private http: HTTP) {}

  listDatasets() {
    return this.http.get<DatasetListResponse>("/api/v1/knowledge/datasets");
  }

  createDataset(name: string) {
    return this.http.post<DatasetInfo>("/api/v1/knowledge/datasets", undefined, {
      name,
    });
  }

  deleteDataset(datasetId: string) {
    return this.http.delete<DeleteResponse>(`/api/v1/knowledge/datasets/${datasetId}`);
  }

  add(data: string, dataset: string) {
    return this.http.post<AddKnowledgeResponse>("/api/v1/knowledge/add", { data, dataset });
  }

  cognify(datasets?: string[], runInBackground = false) {
    const body: Record<string, unknown> = { run_in_background: runInBackground };
    if (datasets !== undefined) body.datasets = datasets;
    return this.http.post<CognifyResponse>("/api/v1/knowledge/cognify", body);
  }

  search(
    query: string,
    opts: { dataset?: string; searchType?: string; topK?: number } = {},
  ) {
    const body: Record<string, unknown> = { query };
    if (opts.dataset !== undefined) body.dataset = opts.dataset;
    if (opts.searchType !== undefined) body.search_type = opts.searchType;
    if (opts.topK !== undefined) body.top_k = opts.topK;
    return this.http.post<KnowledgeSearchResponse>("/api/v1/knowledge/search", body);
  }
}
