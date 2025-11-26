import { ModalContext } from 'components/app/providers/ModalProvider';
import { useContext } from 'react';

const useMyModal = () => {
  return useContext(ModalContext);
};

export default useMyModal;
