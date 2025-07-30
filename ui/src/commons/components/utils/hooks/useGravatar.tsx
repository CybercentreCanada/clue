import { useMemo } from 'react';

const md5 = require('md5');

const useGravatar = (email: string) =>
  useMemo(() => {
    if (email !== null) {
      return `https://s.gravatar.com/avatar/${md5(email)}?d=404`;
    }
    return null;
  }, [email]);

export default useGravatar;
