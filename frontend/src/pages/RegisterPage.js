import React, { useEffect, useState } from "react";
import PasswordChecklist from "react-password-checklist";
import { toast } from "react-toastify";
import { useNavigate } from "react-router-dom";
import { REGISTER_URL } from "../endpoints";
import { axiosInstance } from "../api/axiosPrivate";
const Register = () => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [email, setEmail] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [passwordValidation, setPasswordValidation] = useState(false);
  const navigate = useNavigate();
  
  useEffect(() => {
    var token = localStorage.getItem("token");
    if (token) {
      navigate("/");
    }
  }, []);

  const handleRegister = async (e) => {
    e.preventDefault();
    try {
      if (username.trim() === "") {
        toast.error("Username missing");
        return;
      }
      if (email.trim() === "") {
        toast.error("Email missing");
        return;
      }
      if (!passwordValidation) {
        toast.error("Your password must follow the strenght rules!");
        return;
      }
      
      const data = {username:username,
                    email:email,
                    password: password
                  }
      
      axiosInstance.post(REGISTER_URL, data).then(response => {
        toast.success("Register succesfully, check your email for the confirmation url");
        navigate("/login");
      }).catch(error => {
        // Handle errors
        console.error('An error occurred:', error);
      });
      


    } catch (error) {}
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
                Register
              </h1>
              <form
                className="space-y-4 md:space-y-6"
                action="/"
                onSubmit={handleRegister}
              >
                <div>
                  <label
                    htmlFor="email"
                    className="block mb-2 text-sm font-medium text-gray-900 dark:text-white"
                  >
                    Username
                  </label>
                  <input
                    type="text"
                    name="username"
                    id="username"
                    className="bg-gray-50 border border-gray-300 text-gray-900 rounded-lg focus:ring-primary-600 focus:border-primary-600 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500"
                    placeholder="Your username"
                    required=""
                    onChange={(e) => setUsername(e.target.value)}
                  ></input>
                </div>
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
                    onChange={(e) => setEmail(e.target.value)}
                  ></input>
                </div>
                <div>
                  <label
                    htmlFor="password"
                    className="block mb-2 text-sm font-medium text-gray-900 dark:text-white"
                  >
                    Password
                  </label>
                  <input
                    type="password"
                    name="password"
                    id="password"
                    placeholder="••••••••"
                    className="bg-gray-50 border border-gray-300 text-gray-900 rounded-lg focus:ring-primary-600 focus:border-primary-600 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500"
                    required=""
                    onChange={(e) => setPassword(e.target.value)}
                  ></input>
                </div>
                <div>
                  <label
                    htmlFor="confirmn_password"
                    className="block mb-2 text-sm font-medium text-gray-900 dark:text-white"
                  >
                    Confirm Password
                  </label>
                  <input
                    type="password"
                    name="confirm_password"
                    id="confirm_password"
                    placeholder="••••••••"
                    className="bg-gray-50 border border-gray-300 text-gray-900 rounded-lg focus:ring-primary-600 focus:border-primary-600 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500"
                    required=""
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
                  className="w-full text-white bg-blue-600 hover:bg-blue-700 focus:ring-4 focus:outline-none focus:ring-blue-300 font-medium rounded-lg text-sm px-5 py-2.5 text-center dark:bg-blue-600 dark:hover:bg-blue-700 dark:focus:ring-blue-800"
                >
                  Register
                </button>
                <div className="mt-4 text-center">
                  <span className="text-gray-600">Already an account? </span>
                  <a
                    onClick={() => {navigate("/login/")}}
                    className="text-blue-600 hover:text-blue-800 cursor-pointer"
                  >
                    Sign in
                  </a>
                </div>
              </form>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Register;
