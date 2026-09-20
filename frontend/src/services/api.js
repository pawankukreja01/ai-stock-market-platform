import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  headers: {
    "Content-Type": "application/json",
  },
});

export const getStocks = async () => {
  const response = await api.get("/stocks/");
  return response.data;
};

export const getHistoricalPrices = async (
  stockId,
  startDate,
  endDate
) => {
  const response = await api.get("/historical-prices/", {
    params: {
      stock: stockId,
      start_date: startDate,
      end_date: endDate,
    },
  });

  return response.data;
};

export default api;