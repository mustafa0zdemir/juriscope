import { createBrowserRouter, Navigate } from "react-router-dom";
import MainLayout from "../layouts/MainLayout";
import AuthGuard from "../components/AuthGuard";

export const router = createBrowserRouter([
  {
    path: "/login",
    lazy: async () => ({ Component: (await import("../pages/Login")).default }),
  },
  {
    path: "/register",
    lazy: async () => ({ Component: (await import("../pages/Register")).default }),
  },
  {
    path: "/",
    element: <AuthGuard />,
    children: [
      {
        element: <MainLayout />,
        children: [
          {
            index: true,
            element: <Navigate to="/dashboard" replace />,
          },
          {
            path: "dashboard",
            lazy: async () => ({ Component: (await import("../pages/Dashboard")).default }),
          },
          {
            path: "upload",
            lazy: async () => ({ Component: (await import("../pages/Upload")).default }),
          },
          {
            path: "chat",
            lazy: async () => ({ Component: (await import("../pages/Chat")).default }),
          },
          {
            path: "contracts/:contractId",
            lazy: async () => ({ Component: (await import("../pages/ContractDetail")).default }),
          },
          {
            path: "legal-kb",
            lazy: async () => ({ Component: (await import("../pages/LegalKnowledgeBase")).default }),
          },
          {
            path: "compare",
            lazy: async () => ({ Component: (await import("../pages/ContractComparison")).default }),
          },
          {
            path: "security",
            lazy: async () => ({ Component: (await import("../pages/SecuritySettings")).default }),
          },
        ],
      },
    ],
  },
  {
    path: "*",
    lazy: async () => ({ Component: (await import("../pages/NotFound")).default }),
  },
]);
