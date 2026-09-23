import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "react-toastify";

import { PASSWORD_RESET_URL } from "../endpoints";
import { axiosInstance } from "../api/axiosPrivate";

const ForgotPassword = () => {
  const [email, setEmail] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isSent, setIsSent] = useState(false);

  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (email.trim() === "") {
      toast.error("Email missing");
      return;
    }

    setIsSending(true);
    try {
      await axiosInstance.post(PASSWORD_RESET_URL, { email: email.trim() });
    } catch (error) {
      if (!error?.response) {
        toast.error("Server is down !");
        setIsSending(false);
        return;
      }
    }

    setIsSending(false);
    setIsSent(true);
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
                Forgot your password?
              </h1>

              {isSent ? (
                <div className="space-y-4">
                  <p className="text-sm text-gray-600 dark:text-gray-300">
                    If an account exists for <strong>{email}</strong>, a reset
                    link is on its way. The link expires after 24 hours.
                  </p>
                  <button
                    type="button"
                    onClick={() => navigate("/login/")}
                    className="w-full text-white bg-blue-600 hover:bg-blue-700 focus:ring-4 focus:outline-none focus:ring-blue-300 font-medium rounded-lg text-sm px-5 py-2.5 text-center dark:bg-blue-600 dark:hover:bg-blue-700 dark:focus:ring-blue-800"
                  >
                    Back to sign in
                  </button>
                </div>
              ) : (
                <form className="space-y-4 md:space-y-6" onSubmit={handleSubmit}>
                  <p className="text-sm text-gray-600 dark:text-gray-300">
                    Enter the email you signed up with and we will send you a
                    link to set a new password.
                  </p>
                  <div>
                    <label
                      htmlFor="email"
                      className="block mb-2 text-sm font-medium text-gray-900 dark:text-white"
                    >
                      Email
                    </label>
                    <input
                      type="email"
                      name="email"
                      id="email"
                      className="bg-gray-50 border border-gray-300 text-gray-900 rounded-lg focus:ring-primary-600 focus:border-primary-600 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500"
                      placeholder="user@email.com"
                      required=""
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                    ></input>
                  </div>

                  <button
                    type="submit"
                    disabled={isSending}
                    className="w-full text-white bg-blue-600 hover:bg-blue-700 focus:ring-4 focus:outline-none focus:ring-blue-300 font-medium rounded-lg text-sm px-5 py-2.5 text-center disabled:opacity-60 dark:bg-blue-600 dark:hover:bg-blue-700 dark:focus:ring-blue-800"
                  >
                    {isSending ? "Sending..." : "Send reset link"}
                  </button>
                  <div className="mt-4 text-center">
                    <span className="text-gray-600">
                      Remembered your password?{" "}
                    </span>
                    <Link
                      to="/login/"
                      className="text-blue-600 hover:text-blue-800 cursor-pointer"
                    >
                      Sign in
                    </Link>
                  </div>
                </form>
              )}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default ForgotPassword;
