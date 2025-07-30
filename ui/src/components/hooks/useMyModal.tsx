import { ModalContext } from 'components/app/providers/ModalProvider';
import { useContext } from 'react';

export default function useMyModal() {
  return useContext(ModalContext);
}
