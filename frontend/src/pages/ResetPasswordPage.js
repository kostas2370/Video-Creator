import React, { useEffect, useState } from "react";
import PasswordChecklist from "react-password-checklist";
import { useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "react-toastify";

import {
  PASSWORD_RESET_CONFIRM_URL,
  PASSWORD_RESET_VALIDATE_URL,
} from "../endpoints";
import { axiosInstance } from "../api/axiosPrivate";

const ResetPassword = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";

  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [passwordValidation, setPasswordValidation] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  // "checking" until the backend has had its say on the token, so the form is never
  // filled in against a link that was already used or has expired.
  const [tokenState, setTokenState] = useState("checking");

  const navigate = useNavigate();

  useEffect(() => {
    if (!token) {
      setTokenState("invalid");
      return;
    }

    axiosInstance
      .post(PASSWORD_RESET_VALIDATE_URL, { token })
      .then(() => setTokenState("valid"))
      .catch((error) => {
        // No response at all is the server being down, not a bad token — let the
        // visitor try the form rather than telling them their link is broken.
        setTokenState(error?.response ? "invalid" : "valid");
      });
  }, [token]);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!passwordValidation) {
      toast.error("Your password must follow the strenght rules!");
      return;
    }

    setIsSaving(true);
    axiosInstance
      .post(PASSWORD_RESET_CONFIRM_URL, { token, password })
      .then(() => {
        toast.success("Password changed, you can sign in now");
        navigate("/login/");
      })
      .catch((error) => {
        setIsSaving(false);
        const data = error?.response?.data;
        if (!data) {
          toast.error("Server is down !");
          return;
        }
        // DRF answers with either {"password": [...]} from the validators or
        // {"detail": "..."} when the token went stale between the check and the save.
        const message =
          data.password?.[0] || data.detail || "Could not reset your password";
        toast.error(message);
        if (data.detail) {
          setTokenState("invalid");
        }
      });
  };

  return (
    <div>
      <section className="bg-gray-50 dark:bg-gray-900">
        <div className="flex flex-col items-center justify-center px-6 py-8 mx-auto md:h-screen lg:py-0">
          <a
            href="/"
            className="flex items-center mb-6 text-2xl font-semibold text-gray-900 dark:text-white"
          >
            <img
              className="w-8 h-8 mr-2"
              src="https://flowbite.s3.amazonaws.com/blocks/marketing-ui/logo.svg"
              alt="logo"
            ></img>
            Viddie
          </a>
          <div className="w-full bg-white rounded-lg shadow dark:border md:mt-0 sm:max-w-md xl:p-0 dark:bg-gray-800 dark:border-gray-700">
            <div className="p-6 space-y-4 md:space-y-6 sm:p-8">
              <h1 className="text-xl font-bold leading-tight tracking-tight text-gray-900 md:text-2xl dark:text-white">
                Set a new password
              </h1>

              {tokenState === "checking" ? (
                <p className="text-sm text-gray-600 dark:text-gray-300">
                  Checking your link...
                </p>
              ) : null}

              {tokenState === "invalid" ? (
                <div className="space-y-4">
                  <p className="text-sm text-gray-600 dark:text-gray-300">
                    This reset link is no longer valid — it may have expired or
                    already been used. Ask for a new one and it will land in your
                    inbox.
                  </p>
                  <button
                    type="button"
                    onClick={() => navigate("/forgot-password/")}
                    className="w-full text-white bg-blue-600 hover:bg-blue-700 focus:ring-4 focus:outline-none focus:ring-blue-300 font-medium rounded-lg text-sm px-5 py-2.5 text-center dark:bg-blue-600 dark:hover:bg-blue-700 dark:focus:ring-blue-800"
                  >
                    Request a new link
                  </button>
                </div>
              ) : null}

              {tokenState === "valid" ? (
                <form className="space-y-4 md:space-y-6" onSubmit={handleSubmit}>
                  <div>
                    <label
                      htmlFor="password"
                      className="block mb-2 text-sm font-medium text-gray-900 dark:text-white"
                    >
                      New password
                    </label>
                    <input
                      type="password"
                      name="password"
                      id="password"
                      placeholder="••••••••"
                      className="bg-gray-50 border border-gray-300 text-gray-900 rounded-lg focus:ring-primary-600 focus:border-primary-600 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500"
                      required=""
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                    ></input>
                  </div>
                  <div>
                    <label
                      htmlFor="confirm_password"
                      className="block mb-2 text-sm font-medium text-gray-900 dark:text-white"
                    >
                      Confirm password
                    </label>
                    <input
                      type="password"
                      name="confirm_password"
                      id="confirm_password"
                      placeholder="••••••••"
                      className="bg-gray-50 border border-gray-300 text-gray-900 rounded-lg focus:ring-primary-600 focus:border-primary-600 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500"
                      required=""
                      value={passwordConfirm}
                      onChange={(e) => setPasswordConfirm(e.target.value)}
                    ></input>
                    <br></br>
                    <PasswordChecklist
                      rules={[
                        "minLength",
                        "specialChar",
                        "number",
                        "capital",
                        "match",
                      ]}
                      minLength={8}
                      value={password}
                      valueAgain={passwordConfirm}
                      onChange={(isValid) => {
                        setPasswordValidation(isValid);
                      }}
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={isSaving}
                    className="w-full text-white bg-blue-600 hover:bg-blue-700 focus:ring-4 focus:outline-none focus:ring-blue-300 font-medium rounded-lg text-sm px-5 py-2.5 text-center disabled:opacity-60 dark:bg-blue-600 dark:hover:bg-blue-700 dark:focus:ring-blue-800"
                  >
                    {isSaving ? "Saving..." : "Reset password"}
                  </button>
                </form>
              ) : null}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default ResetPassword;
