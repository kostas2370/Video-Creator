import React from 'react';
import { Navigate, Route } from 'react-router-dom';
import useAuth from './hooks/useAuth';

const PrivateRoute = ({ component: Component, ...rest }) => {

  const {access_token} = useAuth();

  return (
    <Route
      {...rest}
      element={
        access_token ? (
          <Component />
        ) : (
          <Navigate to="/login" replace state={{ from: rest.location }} />
        )
      }
    />
  );
};

export default PrivateRoute;
