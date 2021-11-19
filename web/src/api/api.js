import ENDPOINTS from 'api/endpoints';
const BASE_URL = "http://localhost:8000";

class api {
    constructor(baseUrl, endpoints) {
        this.baseUrl = baseUrl;
        this.endpoints = endpoints;
    }

    async generateRequest(endpoint, data) {
        const {method, uri} = this.endpoints[endpoint];
        let url = new URL(`${this.baseUrl}${uri}`);

        if (["GET"].includes(method)) {
            url.search = new URLSearchParams(data).toString();
            return fetch(url, {method});
        } else {
            return fetch(url, {method, body: data});
        }
    }

    async fetch(endpoint, data) {
        const response = await this.generateRequest(endpoint, data);
        if (!response.ok) {
            throw new Error(`${response.status}: ${response.statusText}`)
        }
        return response.json()
    }
}

export default new api(BASE_URL, ENDPOINTS)